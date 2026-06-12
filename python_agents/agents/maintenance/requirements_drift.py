from __future__ import annotations

import difflib
import hashlib
import os
import re
from datetime import datetime, timezone
from typing import Any

from ..shared.jira import JiraClient, jira_configured
from ..shared.io_utils import read_json, write_json
from ..shared.metadata import extract_metadata
from ..shared.scanner import scan_test_declarations


def run_requirements_drift() -> dict[str, Any]:
    declarations = scan_test_declarations()
    jira_to_tests: dict[str, list[str]] = {}

    for declaration in declarations:
        metadata = extract_metadata(declaration.metadata_text or declaration.title, declaration.file)
        if metadata.jira == "UNKNOWN":
            continue
        jira_to_tests.setdefault(metadata.jira, []).append(metadata.test_id)

    snapshots = read_json("agent-state/python-requirement-snapshots.json", {})
    drift_items: list[dict] = []
    skipped_items: list[dict] = []

    if not jira_configured():
        skipped_items = [
            {
                "jiraKey": jira_key,
                "reason": "Jira environment variables are not configured",
                "linkedTests": linked_tests,
            }
            for jira_key, linked_tests in sorted(jira_to_tests.items())
        ]
    else:
        client = JiraClient()
        for jira_key, linked_tests in sorted(jira_to_tests.items()):
            try:
                issue = client.get_issue(jira_key)
                fields = issue.get("fields", {})
                description = extract_plain_text(fields.get("description"))
                next_hash = hash_text(description)
                acceptance_criteria = extract_acceptance_criteria(description)
                previous = snapshots.get(jira_key)

                if previous and previous.get("hash") != next_hash:
                    ac_changes = diff_acceptance_criteria(
                        previous.get("acceptanceCriteria", []),
                        acceptance_criteria,
                    )
                    drift_items.append({
                        "jiraKey": jira_key,
                        "issueUrl": issue_url(jira_key),
                        "summary": fields.get("summary", ""),
                        "oldHash": previous.get("hash"),
                        "newHash": next_hash,
                        "linkedTests": linked_tests,
                        "updatedAt": fields.get("updated"),
                        "acceptanceCriteriaChanges": ac_changes,
                    })
                    try:
                        client.add_comment(
                            jira_key,
                            build_drift_comment(jira_key, linked_tests, drift_items[-1]),
                        )
                    except Exception as comment_error:  # noqa: BLE001
                        drift_items[-1]["commentStatus"] = f"skipped: {comment_error}"

                snapshots[jira_key] = {
                    "jiraKey": jira_key,
                    "hash": next_hash,
                    "issueUrl": issue_url(jira_key),
                    "summary": fields.get("summary", ""),
                    "updatedAt": fields.get("updated"),
                    "linkedTests": linked_tests,
                    "acceptanceCriteria": acceptance_criteria,
                }
            except Exception as error:  # noqa: BLE001
                skipped_items.append({
                    "jiraKey": jira_key,
                    "reason": str(error),
                    "linkedTests": linked_tests,
                })

    output = {
        "createdAt": datetime.now(timezone.utc).isoformat(),
        "status": "drift_detected" if drift_items else "completed_with_skipped_links" if skipped_items else "no_drift",
        "snapshotCount": len(snapshots),
        "skippedCount": len(skipped_items),
        "driftItems": drift_items,
        "skippedItems": skipped_items,
    }

    write_json("agent-state/python-requirement-snapshots.json", snapshots)
    write_json("agent-state/python-latest-requirement-drift.json", output)
    return output


def hash_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def issue_url(jira_key: str) -> str:
    base_url = os.environ.get("JIRA_BASE_URL", "").rstrip("/")
    return f"{base_url}/browse/{jira_key}" if base_url else jira_key


def extract_plain_text(node: Any) -> str:
    if not node:
        return ""
    if isinstance(node, str):
        return node
    if isinstance(node, list):
        return "\n".join(extract_plain_text(item) for item in node)
    if isinstance(node, dict):
        text = f"{node.get('text', '')}\n" if node.get("text") else ""
        return text + extract_plain_text(node.get("content"))
    return str(node)


def extract_acceptance_criteria(text: str) -> list[str]:
    lines = [_clean_ac_line(line) for line in text.splitlines()]
    lines = [line for line in lines if line]
    if not lines:
        return []

    ac_lines = _extract_acceptance_section(lines)
    if not ac_lines:
        ac_lines = [
            line
            for line in lines
            if re.search(r"\b(given|when|then|should|must|verify|validate|acceptance criteria|ac[-\s]?\d+)\b", line, re.I)
        ]

    return _dedupe_preserve_order(ac_lines)


def diff_acceptance_criteria(previous: list[str], current: list[str]) -> dict[str, Any]:
    previous = _dedupe_preserve_order([_clean_ac_line(item) for item in previous if item])
    current = _dedupe_preserve_order([_clean_ac_line(item) for item in current if item])

    if not previous and current:
        return {
            "status": "baseline_missing",
            "message": "AC changed, but previous snapshot did not store AC text. This run stores it for next comparison.",
            "changed": [],
            "added": current,
            "removed": [],
            "current": current,
        }
    if not previous and not current:
        return {
            "status": "no_ac_section",
            "message": "Description changed, but no Acceptance Criteria section was detected.",
            "changed": [],
            "added": [],
            "removed": [],
            "current": [],
        }

    previous_by_key = {_normalize_for_diff(item): item for item in previous}
    current_by_key = {_normalize_for_diff(item): item for item in current}
    removed = [item for key, item in previous_by_key.items() if key not in current_by_key]
    added = [item for key, item in current_by_key.items() if key not in previous_by_key]
    changed: list[dict[str, str]] = []

    unmatched_added = added[:]
    unmatched_removed: list[str] = []
    for old_item in removed:
        best = _best_match(old_item, unmatched_added)
        if best and best[1] >= 0.65:
            changed.append({"from": old_item, "to": best[0]})
            unmatched_added.remove(best[0])
        else:
            unmatched_removed.append(old_item)

    status = "changed" if changed or unmatched_added or unmatched_removed else "unchanged"
    return {
        "status": status,
        "message": _change_message(changed, unmatched_added, unmatched_removed),
        "changed": changed,
        "added": unmatched_added,
        "removed": unmatched_removed,
        "current": current,
    }


def build_drift_comment(jira_key: str, linked_tests: list[str], drift_item: dict[str, Any]) -> str:
    changes = drift_item.get("acceptanceCriteriaChanges", {})
    lines = [
        "Automation drift detected.",
        f"User story: {issue_url(jira_key)}",
        f"Linked tests require review: {', '.join(linked_tests)}",
        "",
        f"AC change status: {changes.get('status', 'unknown')}",
        changes.get("message", ""),
    ]

    for item in changes.get("changed", [])[:5]:
        lines.extend(["", f"Changed AC: {item.get('from')} -> {item.get('to')}"])
    for item in changes.get("added", [])[:5]:
        lines.append(f"Added AC: {item}")
    for item in changes.get("removed", [])[:5]:
        lines.append(f"Removed AC: {item}")

    return "\n".join(line for line in lines if line is not None)


def _extract_acceptance_section(lines: list[str]) -> list[str]:
    headings = re.compile(r"^(acceptance criteria|acceptance criterion|ac|a/c|criteria)\b[:\s-]*$", re.I)
    stop_headings = re.compile(r"^(description|summary|scope|notes?|attachments?|test cases?|implementation|dev notes?)\b[:\s-]*$", re.I)
    collecting = False
    collected: list[str] = []

    for line in lines:
        if headings.match(line):
            collecting = True
            continue
        if collecting and stop_headings.match(line):
            break
        if collecting:
            collected.append(line)

    return collected


def _clean_ac_line(line: str) -> str:
    cleaned = re.sub(r"^\s*[-*•]\s*", "", line)
    cleaned = re.sub(r"^\s*(?:AC[-\s]?)?\d+[\).:-]\s*", "", cleaned, flags=re.I)
    return re.sub(r"\s+", " ", cleaned).strip()


def _dedupe_preserve_order(items: list[str]) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for item in items:
        key = _normalize_for_diff(item)
        if key and key not in seen:
            seen.add(key)
            result.append(item)
    return result


def _normalize_for_diff(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", " ", value.lower()).strip()


def _best_match(value: str, candidates: list[str]) -> tuple[str, float] | None:
    if not candidates:
        return None
    scored = [
        (candidate, difflib.SequenceMatcher(None, _normalize_for_diff(value), _normalize_for_diff(candidate)).ratio())
        for candidate in candidates
    ]
    return max(scored, key=lambda item: item[1])


def _change_message(changed: list[dict[str, str]], added: list[str], removed: list[str]) -> str:
    parts = []
    if changed:
        parts.append(f"{len(changed)} AC item(s) updated")
    if added:
        parts.append(f"{len(added)} AC item(s) added")
    if removed:
        parts.append(f"{len(removed)} AC item(s) removed")
    return ", ".join(parts) if parts else "No AC text difference detected"
