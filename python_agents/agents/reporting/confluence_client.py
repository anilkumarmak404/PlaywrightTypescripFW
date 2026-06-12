from __future__ import annotations

import html
import os
from collections import defaultdict

from ..maintenance.enterprise import result_summary
from ..shared.confluence import ConfluenceClient, confluence_configured
from ..shared.models import NormalizedTestResult


def update_confluence_report(results: list[NormalizedTestResult], summaries: list[dict], jira_results: list[dict]) -> dict:
    if not confluence_configured(require_page=True):
        return {"status": "skipped", "message": "Confluence environment variables are not configured"}

    try:
        client = ConfluenceClient()
        page_id = os.environ["CONFLUENCE_PAGE_ID"]
        page = client.get_page(page_id)
        html_body = build_confluence_storage(results, summaries, jira_results)
        client.update_page(page_id, page["title"], int(page["version"]["number"]), page.get("status", "current"), html_body)
        return {"status": "updated", "pageId": page_id, "title": page["title"]}
    except Exception as error:  # noqa: BLE001
        return {"status": "failed", "message": str(error)}


def build_confluence_storage(results: list[NormalizedTestResult], summaries: list[dict], jira_results: list[dict]) -> str:
    summary = result_summary(results)
    jira_by_test = {item.get("testId"): item for item in jira_results}
    health = "HEALTHY" if summary["failed"] == 0 else "FAILURES FOUND"
    health_color = "Green" if summary["failed"] == 0 else "Red"

    return f"""
    <h1><strong>Universal Automation Quality Report</strong></h1>
    <table>
      <tr>
        <td><strong>Overall Health</strong><br />{status_macro(health, health_color)}</td>
        <td><strong>Total</strong><br />{status_macro(str(summary['total']), 'Blue')}</td>
        <td><strong>Passed</strong><br />{status_macro(str(summary['passed']), 'Green')}</td>
        <td><strong>Failed</strong><br />{status_macro(str(summary['failed']), 'Red' if summary['failed'] else 'Green')}</td>
        <td><strong>Pass Rate</strong><br />{status_macro(f"{summary['passRate']:.2%}", 'Green' if summary['passRate'] >= 0.9 else 'Red')}</td>
      </tr>
    </table>
    <h2>Feature Quality</h2>
    {breakdown_table(results, "feature")}
    <h2>Owner View</h2>
    {breakdown_table(results, "owner")}
    <h2>Failure Summary</h2>
    <table>
      <tr><th>Test ID</th><th>Classification</th><th>Owner</th><th>Summary</th><th>Suggested Action</th><th>Jira</th></tr>
      {''.join(failure_row(item, jira_by_test.get(item.get('testId'))) for item in summaries) or f'<tr><td colspan="6">{status_macro("NO FAILURES", "Green")}</td></tr>'}
    </table>
    <h2>Latest Result Snapshot</h2>
    <table>
      <tr><th>Test ID</th><th>Status</th><th>Framework</th><th>Feature</th><th>Owner</th><th>Duration</th></tr>
      {''.join(result_row(item) for item in results[:25]) or f'<tr><td colspan="6">{status_macro("NO RESULTS", "Grey")}</td></tr>'}
    </table>
    """


def status_macro(title: str, colour: str) -> str:
    return (
        '<ac:structured-macro ac:name="status" ac:schema-version="1">'
        f'<ac:parameter ac:name="title">{html.escape(title)}</ac:parameter>'
        f'<ac:parameter ac:name="colour">{colour}</ac:parameter>'
        '<ac:parameter ac:name="subtle">false</ac:parameter>'
        '</ac:structured-macro>'
    )


def breakdown_table(results: list[NormalizedTestResult], field: str) -> str:
    groups: dict[str, list[NormalizedTestResult]] = defaultdict(list)
    for result in results:
        groups[getattr(result, field) or "unknown"].append(result)

    rows = []
    for name, items in sorted(groups.items()):
        summary = result_summary(items)
        rows.append(
            f"<tr><td><strong>{html.escape(name)}</strong></td>"
            f"<td>{summary['total']}</td>"
            f"<td>{status_macro(str(summary['passed']), 'Green')}</td>"
            f"<td>{status_macro(str(summary['failed']), 'Red' if summary['failed'] else 'Green')}</td>"
            f"<td>{status_macro(str(summary['skipped']), 'Yellow' if summary['skipped'] else 'Green')}</td>"
            f"<td>{status_macro(f'{summary['passRate']:.2%}', 'Green' if summary['passRate'] >= 0.9 else 'Red')}</td></tr>"
        )

    return (
        "<table><tr><th>Name</th><th>Total</th><th>Passed</th><th>Failed</th><th>Skipped</th><th>Pass Rate</th></tr>"
        + ("".join(rows) or f'<tr><td colspan="6">{status_macro("NO DATA", "Grey")}</td></tr>')
        + "</table>"
    )


def failure_row(summary: dict, jira: dict | None) -> str:
    jira_text = "Not created"
    if jira and jira.get("issueUrl"):
        jira_text = f'<a href="{html.escape(jira["issueUrl"])}">{html.escape(jira.get("issueKey", ""))}</a> ({html.escape(jira.get("status", ""))})'
    elif jira and jira.get("message"):
        jira_text = f"Skipped: {html.escape(jira['message'])}"
    return (
        "<tr>"
        f"<td><strong>{html.escape(str(summary.get('testId', 'unknown')))}</strong></td>"
        f"<td>{status_macro(str(summary.get('classification', 'unknown')).upper(), 'Red')}</td>"
        f"<td>{html.escape(str(summary.get('owner', 'unknown')))}</td>"
        f"<td>{html.escape(str(summary.get('summary', '')))}</td>"
        f"<td>{html.escape(str(summary.get('suggestedAction', '')))}</td>"
        f"<td>{jira_text}</td>"
        "</tr>"
    )


def result_row(result: NormalizedTestResult) -> str:
    color = "Green" if result.status == "passed" else "Red" if result.status in {"failed", "timedOut"} else "Yellow"
    return (
        "<tr>"
        f"<td><strong>{html.escape(result.test_id)}</strong></td>"
        f"<td>{status_macro(result.status.upper(), color)}</td>"
        f"<td>{html.escape(result.framework)}</td>"
        f"<td>{html.escape(result.feature)}</td>"
        f"<td>{html.escape(result.owner)}</td>"
        f"<td>{result.duration_ms} ms</td>"
        "</tr>"
    )
