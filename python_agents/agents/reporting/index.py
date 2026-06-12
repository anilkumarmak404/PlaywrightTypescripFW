from __future__ import annotations

from collections.abc import Callable
from datetime import datetime, timezone
from typing import Any

from .confluence_client import update_confluence_report
from .failure_summary import summarize_failures
from .grafana_metrics import push_grafana_metrics
from .jira_client import upsert_jira_bugs
from .parse_results import parse_latest_agent_results
from .slack_digest import send_daily_slack_digest
from ..maintenance.enterprise import write_enterprise_markdown
from ..shared.io_utils import write_json
from ..shared.models import Finding, NormalizedTestResult


def run_reporting_agent(
    results: list[NormalizedTestResult] | None = None,
    findings: list[Finding] | None = None,
) -> dict[str, Any]:
    print("Reporting Agent started")
    active_results = results if results is not None else parse_latest_agent_results()
    active_findings = findings or []
    failures = [item for item in active_results if item.status in {"failed", "timedOut"}]
    summaries = summarize_failures(failures)
    jira_results = upsert_jira_bugs(failures, summaries)

    latest_summary = {
        "createdAt": datetime.now(timezone.utc).isoformat(),
        "total": len(active_results),
        "failures": len(failures),
        "summaries": summaries,
        "jira": jira_results,
    }
    write_json("agent-state/latest-reporting-summary.json", latest_summary)
    write_json("agent-state/python-latest-reporting-summary.json", latest_summary)

    optional_results = {
        "grafana": _run_optional("Push Grafana metrics", lambda: push_grafana_metrics(active_results)),
        "confluence": _run_optional("Update Confluence report", lambda: update_confluence_report(active_results, summaries, jira_results)),
        "slack": _run_optional("Send Slack digest", lambda: send_daily_slack_digest(active_results, summaries)),
    }

    output = {
        **latest_summary,
        **optional_results,
    }
    write_json("reports/ai-summary/python-agent-summary.json", {
        "summary": _result_summary(active_results),
        "findingCount": len(active_findings),
        "findings": [finding.to_dict() for finding in active_findings],
        "failureSummaries": summaries,
        "jira": jira_results,
        **optional_results,
    })
    write_enterprise_markdown(active_results, active_findings)
    print("Reporting Agent completed")
    return output


def write_normalized_results(results: list[NormalizedTestResult]) -> None:
    run_id = results[0].run_id if results else f"empty-{datetime.now(timezone.utc).timestamp()}"
    write_json("reports/ai-summary/python-normalized-results.json", {
        "runId": run_id,
        "results": [result.to_dict() for result in results],
    })


def write_reporting_outputs(results: list[NormalizedTestResult], findings: list[Finding]) -> None:
    run_reporting_agent(results, findings)


def _run_optional(name: str, action: Callable[[], Any]) -> dict[str, Any]:
    try:
        result = action()
        if isinstance(result, dict):
            return result
        return {"status": "completed"}
    except Exception as error:  # noqa: BLE001
        message = str(error)
        print(f"{name} skipped: {message}")
        return {"status": "skipped", "message": message}


def _result_summary(results: list[NormalizedTestResult]) -> dict[str, Any]:
    total = len(results)
    passed = sum(1 for item in results if item.status == "passed")
    failed = sum(1 for item in results if item.status in {"failed", "timedOut"})
    skipped = sum(1 for item in results if item.status == "skipped")
    flaky = sum(1 for item in results if item.status == "flaky")
    unknown = sum(1 for item in results if item.status == "unknown")
    return {
        "total": total,
        "passed": passed,
        "failed": failed,
        "skipped": skipped,
        "flaky": flaky,
        "unknown": unknown,
        "passRate": passed / total if total else 0,
    }
