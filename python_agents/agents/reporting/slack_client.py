from __future__ import annotations

from typing import Any

from ..shared.models import Finding, NormalizedTestResult
from ..shared.slack import send_slack_message


def send_execution_summary(
    summary: dict[str, Any],
    failures: list[NormalizedTestResult],
    failure_summaries: list[dict],
    findings: list[Finding],
    jira_results: list[dict],
    confluence_result: dict[str, Any],
) -> dict[str, Any]:
    top_failures = "\n".join(
        f"- `{item.get('testId')}` - {item.get('classification')} - {item.get('owner')}"
        for item in failure_summaries[:5]
    ) or "No failures"

    jira_created = sum(1 for item in jira_results if item.get("status") == "created")
    jira_updated = sum(1 for item in jira_results if item.get("status") == "updated")
    jira_skipped = sum(1 for item in jira_results if item.get("status") == "skipped")

    text = "\n".join([
        f"*Total:* {summary['total']}",
        f"*Passed:* {summary['passed']}",
        f"*Failed:* {summary['failed']}",
        f"*Skipped:* {summary['skipped']}",
        f"*Flaky:* {summary['flaky']}",
        f"*Unknown:* {summary['unknown']}",
        f"*Pass rate:* {summary['passRate']:.2%}",
        f"*Enterprise findings:* {len(findings)}",
        f"*Failure count:* {len(failures)}",
        "",
        "*Jira sync:* "
        f"created {jira_created}, updated {jira_updated}, skipped {jira_skipped}",
        f"*Confluence:* {confluence_result.get('status', 'unknown')}",
        "",
        "*Top failures:*",
        top_failures,
    ])

    return send_slack_message("Python Automation Execution Summary", text)


def send_enterprise_summary(findings: list[Finding]) -> dict[str, Any]:
    severity_counts = {
        "high": sum(1 for item in findings if item.severity == "high"),
        "medium": sum(1 for item in findings if item.severity == "medium"),
        "low": sum(1 for item in findings if item.severity == "low"),
    }
    top_findings = "\n".join(
        f"- *{item.severity.upper()}* {item.type}: {item.message}"
        for item in findings[:8]
    ) or "No enterprise readiness findings"

    text = "\n".join([
        f"*Total findings:* {len(findings)}",
        f"*High:* {severity_counts['high']}",
        f"*Medium:* {severity_counts['medium']}",
        f"*Low:* {severity_counts['low']}",
        "",
        "*Top findings:*",
        top_findings,
    ])

    return send_slack_message("Python Enterprise Readiness Summary", text)


def send_maintenance_summary(findings: list[Finding]) -> dict[str, Any]:
    severity_counts = {
        "high": sum(1 for item in findings if item.severity == "high"),
        "medium": sum(1 for item in findings if item.severity == "medium"),
        "low": sum(1 for item in findings if item.severity == "low"),
    }
    by_type: dict[str, int] = {}
    for finding in findings:
        by_type[finding.type] = by_type.get(finding.type, 0) + 1

    type_summary = ", ".join(f"{key}: {value}" for key, value in sorted(by_type.items())) or "none"
    top_findings = "\n".join(
        f"- *{item.severity.upper()}* {item.type}: {item.message}"
        for item in sorted(findings, key=lambda item: {"high": 3, "medium": 2, "low": 1}.get(item.severity, 0), reverse=True)[:8]
    ) or "No maintenance findings"

    text = "\n".join([
        f"*Total findings:* {len(findings)}",
        f"*Severity:* High {severity_counts['high']}, Medium {severity_counts['medium']}, Low {severity_counts['low']}",
        f"*Types:* {type_summary}",
        "",
        "*Top findings:*",
        top_findings,
    ])

    return send_slack_message("Maintenance Agent findings", text)


def send_requirements_summary(requirement_result: dict[str, Any]) -> dict[str, Any]:
    drift_items = requirement_result.get("driftItems", [])
    skipped_items = requirement_result.get("skippedItems", [])
    top_drift = "\n".join(
        _format_requirement_drift_item(item)
        for item in drift_items[:8]
    ) or "No drift detected"
    top_skipped = "\n".join(
        f"- `{item.get('jiraKey')}` linked tests: {', '.join(item.get('linkedTests', []))}"
        for item in skipped_items[:8]
    ) or "No skipped links"

    text = "\n".join([
        f"*Status:* {requirement_result.get('status', 'unknown')}",
        f"*Snapshots:* {requirement_result.get('snapshotCount', 0)}",
        f"*Drift items:* {len(drift_items)}",
        f"*Skipped Jira links:* {requirement_result.get('skippedCount', 0)}",
        "",
        "*Drift:*",
        top_drift,
        "",
        "*Skipped links:*",
        top_skipped,
    ])

    return send_slack_message("Python Requirements Drift Summary", text)


def _format_requirement_drift_item(item: dict[str, Any]) -> str:
    issue_key = item.get("jiraKey", "<unknown>")
    issue_url = item.get("issueUrl") or issue_key
    linked_tests = ", ".join(item.get("linkedTests", []))
    ac_changes = item.get("acceptanceCriteriaChanges") or {}
    status = ac_changes.get("status", "unknown")
    message = ac_changes.get("message", "")
    changed = ac_changes.get("changed", [])
    added = ac_changes.get("added", [])
    removed = ac_changes.get("removed", [])

    detail = ""
    if changed:
        first = changed[0]
        detail = f" changed: `{first.get('from')}` -> `{first.get('to')}`"
    elif added:
        detail = f" added: `{added[0]}`"
    elif removed:
        detail = f" removed: `{removed[0]}`"
    elif message:
        detail = f" {message}"

    return f"- <{issue_url}|{issue_key}> AC `{status}`{detail}. Linked tests: {linked_tests}"


def send_jira_check_summary(jira_result: dict[str, Any]) -> dict[str, Any]:
    user = jira_result.get("user") or {}
    env = jira_result.get("env") or {}
    text = "\n".join([
        f"*Status:* {jira_result.get('status', 'unknown')}",
        f"*User:* {user.get('displayName') or user.get('accountId') or '<unknown>'}",
        f"*Project access:* {jira_result.get('projectAccess', '<not checked>')}",
        f"*Project key:* {env.get('projectKey') or '<missing>'}",
        f"*Base URL:* {env.get('baseUrl') or '<missing>'}",
        f"*Message:* {jira_result.get('message') or jira_result.get('projectAccessMessage') or 'OK'}",
    ])

    return send_slack_message("Python Jira Check Summary", text)


def send_weekly_report_summary(weekly_result: dict[str, Any]) -> dict[str, Any]:
    summary = weekly_result.get("summary") or {}
    text = "\n".join([
        f"*Status:* {weekly_result.get('status', 'unknown')}",
        f"*Total:* {summary.get('total', 0)}",
        f"*Passed:* {summary.get('passed', 0)}",
        f"*Failed:* {summary.get('failed', 0)}",
        f"*Skipped:* {summary.get('skipped', 0)}",
        f"*Pass rate:* {summary.get('passRate', 0):.2%}",
    ])
    report_paths = "\n".join([
        f"*HTML:* {weekly_result.get('htmlPath', '<not generated>')}",
        f"*PDF:* {weekly_result.get('pdfPath', '<not generated>')}",
    ])

    return send_slack_message(
        "Python Weekly Quality Scorecard Summary",
        text,
        attachment_text=report_paths,
        attachment_color="#d32f2f",
    )


def send_chaos_summary(chaos_result: dict[str, Any]) -> dict[str, Any]:
    rows = "\n".join(
        f"- `{item.get('status')}` {item.get('scenario')}: {item.get('detail')}"
        for item in chaos_result.get("results", [])[:8]
    ) or "No chaos scenarios recorded"

    text = "\n".join([
        f"*Total scenarios:* {chaos_result.get('total', 0)}",
        f"*Failed:* {chaos_result.get('failed', 0)}",
        "",
        "*Scenarios:*",
        rows,
    ])

    return send_slack_message("Python Chaos Validation Summary", text)
