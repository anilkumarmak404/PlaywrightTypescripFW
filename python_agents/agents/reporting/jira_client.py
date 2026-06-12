from __future__ import annotations

import os
from typing import Any

from ..shared.fingerprint import create_failure_fingerprint
from ..shared.jira import JiraClient, jira_configured, jira_env_summary
from ..shared.models import NormalizedTestResult


def check_jira_auth() -> dict[str, Any]:
    summary = jira_env_summary()
    if not jira_configured():
        return {"status": "skipped", "message": "Jira environment variables are not configured", "env": summary}

    try:
        client = JiraClient()
        user = client.verify_auth()
    except Exception as error:  # noqa: BLE001
        return {"status": "failed", "message": str(error), "env": summary}

    access_status = "not_checked"
    access_message = ""
    try:
        client.validate_access()
        access_status = "ok"
    except Exception as error:  # noqa: BLE001
        access_status = "failed"
        access_message = str(error)

    return {
        "status": "ok" if access_status == "ok" else "partial",
        "user": {
            "accountId": user.get("accountId"),
            "displayName": user.get("displayName"),
        },
        "projectAccess": access_status,
        "projectAccessMessage": access_message,
        "env": summary,
    }


def upsert_jira_bugs(failures: list[NormalizedTestResult], summaries: list[dict]) -> list[dict]:
    if not failures:
        return []
    if not jira_configured(require_project=True):
        return [
            {"testId": failure.test_id, "status": "skipped", "message": "Jira environment variables are not configured"}
            for failure in failures
        ]

    try:
        client = JiraClient()
        client.validate_access()
    except Exception as error:  # noqa: BLE001
        return [{"testId": failure.test_id, "status": "skipped", "message": str(error)} for failure in failures]

    results: list[dict] = []
    by_test_id = {summary["testId"]: summary for summary in summaries}

    for failure in failures:
        try:
            summary = by_test_id.get(failure.test_id, {})
            fingerprint = create_failure_fingerprint(failure)
            title = build_bug_title(failure, summary)
            description = build_bug_description(failure, summary)
            gherkin_steps = build_gherkin_steps(failure, summary)
            existing = client.search_by_fingerprint(fingerprint)

            if existing:
                issue_key = existing["key"]
                client.update_summary(issue_key, title)
                client.add_comment(
                    issue_key,
                    "\n".join([
                        f"Failure reproduced again for test {failure.test_id}. Run ID: {failure.run_id}",
                        "",
                        "Bug Reproduction Steps - Cucumber / Gherkin",
                        gherkin_steps,
                    ]),
                )
                status = "updated"
            else:
                issue = client.create_bug(title, description, fingerprint, [failure.feature, failure.owner])
                issue_key = issue["key"]
                status = "created"

            for artifact in [failure.trace_path, failure.screenshot_path, failure.video_path]:
                client.attach_file(issue_key, artifact)

            results.append({
                "testId": failure.test_id,
                "status": status,
                "issueKey": issue_key,
                "issueUrl": f"{os.environ['JIRA_BASE_URL'].rstrip('/')}/browse/{issue_key}",
            })
        except Exception as error:  # noqa: BLE001
            results.append({"testId": failure.test_id, "status": "skipped", "message": str(error)})

    return results


def build_bug_title(failure: NormalizedTestResult, summary: dict) -> str:
    feature = _title_case(failure.feature)
    classification = _title_case(str(summary.get("classification", "unknown")))
    status = _title_case(failure.status)
    return f"[Playwright Failure] {feature} - {failure.test_id} {status} ({classification})"


def build_bug_description(failure: NormalizedTestResult, summary: dict) -> str:
    gherkin_steps = build_gherkin_steps(failure, summary)
    return "\n".join([
        "Automated Playwright Failure",
        "",
        "Failure Details",
        f"Test ID: {failure.test_id}",
        f"Test Title: {failure.title}",
        f"Feature: {_title_case(failure.feature)}",
        f"Owner: {failure.owner}",
        f"Status: {failure.status}",
        f"Classification: {summary.get('classification', 'unknown')}",
        f"Run ID: {failure.run_id}",
        f"File: {failure.file}",
        "",
        "Impact Summary",
        str(summary.get("summary", "No summary available")),
        "",
        "Probable Cause",
        str(summary.get("probableCause", failure.error_message or "Unknown")),
        "",
        "Suggested Action",
        str(summary.get("suggestedAction", "Review failure artifacts")),
        "",
        "Bug Reproduction Steps - Cucumber / Gherkin",
        gherkin_steps,
    ])


def build_gherkin_steps(failure: NormalizedTestResult, summary: dict | None = None) -> str:
    return "\n".join([
        "Feature: Automated Playwright failure triage",
        "",
        f"  Scenario: {failure.test_id} fails in {failure.feature}",
        f'    Given the test "{failure.test_id}" is executed from "{failure.file}"',
        f'    And the feature under test is "{failure.feature}"',
        f'    And the owning team is "{failure.owner}"',
        f'    When the Playwright test run "{failure.run_id}" reaches this scenario',
        f'    Then the test status should be "{failure.status}"',
        f'    And the failure should be classified as "{(summary or {}).get("classification", "unknown")}"',
        f'    And the probable cause should be "{(summary or {}).get("probableCause", failure.error_message or "Unknown")}"',
        f'    And the suggested action should be "{(summary or {}).get("suggestedAction", "Review failure artifacts")}"',
    ])


def _title_case(value: str) -> str:
    words = [word for word in value.replace("_", " ").replace("-", " ").split() if word]
    return " ".join(f"{word[:1].upper()}{word[1:]}" for word in words)
