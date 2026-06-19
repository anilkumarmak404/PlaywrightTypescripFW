from __future__ import annotations

import json
import os
import queue
import subprocess
import sys
import threading
import time
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import streamlit as st


ROOT = Path(__file__).resolve().parents[2]

COMMANDS = {
    "Normalize results": "normalize",
    "Maintenance": "maintenance",
    "Enterprise readiness": "enterprise",
    "Requirements drift": "requirements",
    "Reporting": "reporting",
    "Jira auth check": "jira-check",
    "Weekly PDF": "weekly-pdf",
    "Chaos": "chaos",
}

DEFAULT_ENVIRONMENTS = ["demo", "qa", "dev"]

OUTPUT_FILES = {
    "Agent summary": "reports/ai-summary/python-agent-summary.json",
    "Normalized results": "reports/ai-summary/python-normalized-results.json",
    "Maintenance findings": "agent-state/python-latest-maintenance-findings.json",
    "Requirements drift": "agent-state/python-latest-requirement-drift.json",
    "Jira auth check": "agent-state/python-jira-auth-check.json",
    "Weekly report": "agent-state/python-weekly-report.json",
    "Chaos results": "agent-state/python-latest-chaos-results.json",
    "Slack notifications": "agent-state/python-slack-notifications.json",
    "Playwright UI runs": "agent-state/streamlit-playwright-runs.json",
}

AGENT_STAGE_DEFINITIONS = [
    ("agent:normalize", "Normalize Results"),
    ("agent:maintenance", "Maintenance"),
    ("agent:reporting", "Report Agent"),
    ("agent:requirements", "Drift Agent"),
    ("agent:jira", "Jira Check"),
    ("agent:weekly", "Weekly PDF"),
    ("agent:chaos", "Chaos"),
    ("allure:ports", "Allure Ports 5050 / 5051"),
]

AGENT_STAGE_BY_COMMAND = {
    "normalize": [("agent:normalize", "Normalize Results")],
    "maintenance": [("agent:maintenance", "Maintenance")],
    "enterprise": [("agent:enterprise", "Enterprise Readiness")],
    "requirements": [("agent:requirements", "Drift Agent")],
    "reporting": [("agent:reporting", "Report Agent")],
    "jira-check": [("agent:jira", "Jira Check")],
    "weekly-pdf": [("agent:weekly", "Weekly PDF")],
    "chaos": [("agent:chaos", "Chaos")],
    "all": AGENT_STAGE_DEFINITIONS,
}

GRAFANA_DASHBOARD_URL = (
    "http://localhost:3000/d/playwright-quality/playwright-quality-dashboard"
    "?orgId=1&from=now%2Fd&to=now&timezone=browser&refresh=10s"
)
CONFLUENCE_REPORT_URL = (
    "https://anilkumarqa801.atlassian.net/wiki/spaces/~71202011836adaf02f42acb66ab275ec62a527/"
    "pages/426019/Test+Report"
)
SLACK_CHANNEL_URL = "https://app.slack.com/client/T0B7EJYA6AZ/C0B72GXAFP1"
GITHUB_REPOSITORY_URL = "https://github.com/anilkumarmak404/PlaywrightTypescripFW"


def main() -> None:
    st.set_page_config(page_title="Automation Agent Control Center", layout="wide")
    _inject_styles()

    playwright_scripts = _playwright_scripts()
    _render_header()

    with st.sidebar:
        st.header("Run Controls")
        environments = _available_environments()
        env_name = st.selectbox("Environment", environments, index=_environment_index(environments, "demo"))
        sidebar_default_scripts = _default_playwright_selection(playwright_scripts)
        sidebar_script = st.selectbox(
            "Playwright script",
            options=list(playwright_scripts.keys()),
            index=_selected_script_index(playwright_scripts, sidebar_default_scripts[0] if sidebar_default_scripts else ""),
            help="Select one package.json Playwright script.",
        )
        result_globs = ""
        st.text_area(
            "Execution plan",
            value=_script_plan_text(sidebar_script, playwright_scripts),
            height=96,
            disabled=True,
        )
        run_playwright_flow = st.button("Run Playwright Flow", type="primary", width="stretch")
        run_script_reporting = st.button(f"Run {sidebar_script} + Reporting Agent", width="stretch")

        st.divider()
        selected_label = st.selectbox("Agent", list(COMMANDS.keys()), index=0)
        selected_command = COMMANDS[selected_label]
        run_selected = st.button("Submit Agent", width="stretch")

        st.button("Refresh Dashboard", width="stretch")

        st.divider()
        st.link_button("Open Grafana Dashboard", _grafana_dashboard_url(), width="stretch")

    if run_playwright_flow:
        _run_scripts_then_agent([sidebar_script], playwright_scripts, True, env_name, result_globs, None)
    if run_script_reporting:
        _run_scripts_then_agent([sidebar_script], playwright_scripts, True, env_name, result_globs, "reporting")
    if run_selected:
        _run_and_render(selected_command, env_name, "auto", result_globs)

    summary = _read_json(OUTPUT_FILES["Agent summary"], {})
    maintenance = _read_json(OUTPUT_FILES["Maintenance findings"], {})
    requirements = _read_json(OUTPUT_FILES["Requirements drift"], {})
    weekly = _read_json(OUTPUT_FILES["Weekly report"], {})
    chaos = _read_json(OUTPUT_FILES["Chaos results"], {})
    slack = _read_json(OUTPUT_FILES["Slack notifications"], {})
    playwright_runs = _read_json(OUTPUT_FILES["Playwright UI runs"], {})

    _render_main_execution_progress(playwright_runs)
    _render_quick_result(
        _active_quick_view(),
        summary,
        maintenance,
        requirements,
        weekly,
        chaos,
        slack,
        playwright_runs,
    )
    _render_overview(summary, maintenance, requirements, weekly, chaos, slack)

    tabs = st.tabs([
        "Playwright Runs",
        "Maintenance",
        "Requirements",
        "Reporting",
        "Weekly Report",
        "Chaos",
        "Ollama Assistant",
        "Raw Outputs",
    ])
    with tabs[0]:
        _render_playwright_runs(playwright_scripts, playwright_runs, env_name, result_globs)
    with tabs[1]:
        _render_maintenance(maintenance)
    with tabs[2]:
        _render_requirements(requirements)
    with tabs[3]:
        _render_reporting(summary, slack)
    with tabs[4]:
        _render_weekly_report(weekly)
    with tabs[5]:
        _render_chaos(chaos)
    with tabs[6]:
        _render_ollama_assistant(summary, maintenance, requirements, chaos)
    with tabs[7]:
        _render_raw_outputs()


def _run_and_render(command: str, env_name: str, framework: str, result_globs: str) -> None:
    st.subheader(f"Running: {command}")
    with st.spinner("Agent command is running..."):
        result = _run_agent(command, env_name, framework, result_globs)

    if result["returncode"] == 0:
        st.success("Agent command completed successfully.")
    else:
        st.error(f"Agent command failed with exit code {result['returncode']}.")

    with st.expander("Command output", expanded=True):
        st.code(result["command"], language="powershell")
        if result["stdout"]:
            st.text_area("stdout", result["stdout"], height=180)
        if result["stderr"]:
            st.text_area("stderr", result["stderr"], height=180)


def _run_scripts_then_agents(
    selected_scripts: list[str],
    scripts: dict[str, str],
    stop_on_failure: bool,
    env_name: str,
    result_globs: str,
    timeout_seconds: int = 1800,
    render: bool = True,
) -> dict[str, Any]:
    return _run_scripts_then_agent(
        selected_scripts,
        scripts,
        stop_on_failure,
        env_name,
        result_globs,
        "all",
        timeout_seconds,
        render,
    )


def _run_scripts_then_agent(
    selected_scripts: list[str],
    scripts: dict[str, str],
    stop_on_failure: bool,
    env_name: str,
    result_globs: str,
    agent_command: str | None,
    timeout_seconds: int = 1800,
    render: bool = True,
) -> dict[str, Any]:
    if not selected_scripts:
        st.warning("Select at least one Playwright script.")
        return {}

    stages = _build_execution_stages(selected_scripts, AGENT_STAGE_BY_COMMAND.get(agent_command, []))
    progress_placeholder = st.empty()
    current_placeholder = st.empty()
    board_placeholder = st.empty()
    output_placeholder = st.empty()
    started = time.monotonic()
    _render_execution_monitor(stages, progress_placeholder, board_placeholder, current_placeholder, "Queued")

    results = []
    for script_name in selected_scripts:
        stage_key = f"playwright:{script_name}"
        _set_stage_status(stages, stage_key, "running", 5)
        _render_execution_monitor(stages, progress_placeholder, board_placeholder, current_placeholder, f"Playwright: {script_name}")

        result = _run_npm_script_live(
            script_name,
            scripts[script_name],
            timeout_seconds,
            on_output=lambda line, name=script_name, key=stage_key: (
                _bump_running_stage(stages, key, 5),
                _render_execution_monitor(stages, progress_placeholder, board_placeholder, current_placeholder, f"Playwright: {name}"),
                _render_execution_output(output_placeholder, name, line),
            ),
        )
        results.append(result)
        _set_stage_status(stages, stage_key, "done" if result["returncode"] == 0 else "failed")
        _render_execution_monitor(stages, progress_placeholder, board_placeholder, current_placeholder, f"Completed: {script_name}")

        if stop_on_failure and result["returncode"] != 0:
            _skip_remaining_playwright_stages(stages, selected_scripts, script_name)
            break

    post_result = None
    if agent_command:
        first_stage = AGENT_STAGE_BY_COMMAND.get(agent_command, [])[0][0]
        _set_stage_status(stages, first_stage, "running", 5)
        _render_execution_monitor(stages, progress_placeholder, board_placeholder, current_placeholder, f"Agent: {agent_command}")
        post_result = _run_agent_command_live(
            agent_command,
            env_name,
            result_globs,
            stages,
            progress_placeholder,
            board_placeholder,
            current_placeholder,
            output_placeholder,
        )

    failed = sum(1 for item in results if item["returncode"] != 0)
    run_result = {
        "createdAt": datetime.now(timezone.utc).isoformat(),
        "selectedScripts": selected_scripts,
        "stopOnFailure": stop_on_failure,
        "total": len(results),
        "passed": len(results) - failed,
        "failed": failed,
        "durationSeconds": time.monotonic() - started,
        "stages": stages,
        "results": results,
        "postRun": {
            "label": _agent_run_label(agent_command),
            "result": post_result,
        },
    }
    _write_json("agent-state/streamlit-playwright-runs.json", run_result)
    _render_execution_monitor(stages, progress_placeholder, board_placeholder, current_placeholder, "Completed")

    if render:
        _render_playwright_run_result(run_result)

    return run_result


def _run_agent(command: str, env_name: str, framework: str, result_globs: str) -> dict[str, Any]:
    args = [
        sys.executable,
        "-m",
        "python_agents.cli",
        command,
        "--env",
        env_name,
        "--framework",
        framework,
    ]

    globs = _parse_result_globs(result_globs)
    if globs:
        args.append("--results")
        args.extend(globs)

    env = os.environ.copy()
    env["ENV_NAME"] = env_name
    env["PYTHONUTF8"] = "1"

    try:
        completed = subprocess.run(
            args,
            cwd=ROOT,
            env=env,
            text=True,
            capture_output=True,
            timeout=900,
            check=False,
        )
        return {
            "command": _display_command(args),
            "returncode": completed.returncode,
            "stdout": completed.stdout,
            "stderr": completed.stderr,
        }
    except subprocess.TimeoutExpired as error:
        return {
            "command": _display_command(args),
            "returncode": 124,
            "stdout": error.stdout or "",
            "stderr": f"Timed out after {error.timeout} seconds.",
        }


def _render_header() -> None:
    st.markdown(
        f"""
        <div class="app-hero">
          <div>
            <div class="hero-kicker">Local automation command center</div>
            <h1>Automation Agent Control Center</h1>
            <p>Run Playwright scripts, launch Python agents, and inspect quality signals from one localhost dashboard.</p>
          </div>
          <div class="hero-badges">
            <a class="badge blue" href="?quick=playwright">Playwright</a>
            <a class="badge green" href="?quick=agents">Python Agents</a>
            <a class="badge violet" href="?quick=reporter">Reporter</a>
            <a class="badge red" href="?quick=slack">Slack</a>
            <a class="badge amber" href="?quick=confluence">Confluence</a>
            <a class="badge teal" href="?quick=grafana">Grafana</a>
            <a class="badge dark" href="{GITHUB_REPOSITORY_URL}" target="_blank">
              <span class="github-mark">GH</span> GitHub
            </a>
          </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def _render_quick_result(
    view: str,
    summary: dict[str, Any],
    maintenance: dict[str, Any],
    requirements: dict[str, Any],
    weekly: dict[str, Any],
    chaos: dict[str, Any],
    slack: dict[str, Any],
    playwright_runs: dict[str, Any],
) -> None:
    if not view:
        return

    titles = {
        "playwright": "Latest Playwright Result",
        "agents": "Latest Python Agent Result",
        "reporter": "Latest Reporter Output",
        "slack": "Latest Slack Result",
        "confluence": "Latest Confluence Result",
        "grafana": "Latest Grafana Result",
    }
    st.markdown(
        f"""
        <div class="quick-panel">
          <div class="quick-title">{titles.get(view, "Latest Result")}</div>
          <div class="quick-caption">Showing the latest saved output for the selected header link.</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    if view == "playwright":
        _render_quick_playwright(playwright_runs)
    elif view == "agents":
        _render_quick_agents(summary, maintenance, requirements, chaos)
    elif view == "reporter":
        _render_quick_reporter(summary, weekly)
    elif view == "slack":
        _render_quick_slack(summary, slack)
    elif view == "confluence":
        _render_quick_confluence(summary)
    elif view == "grafana":
        _render_quick_grafana(summary)
    else:
        st.info("Unknown quick view.")

def _render_quick_playwright(data: dict[str, Any]) -> None:
    if not data:
        st.info("No dashboard-triggered Playwright run is available yet. Select a script and click Run Playwright Flow.")
        return

    cols = st.columns(4)
    cols[0].metric("Scripts", _num(data.get("total")))
    cols[1].metric("Passed", _num(data.get("passed")))
    cols[2].metric("Failed", _num(data.get("failed")))
    cols[3].metric("Duration", f"{data.get('durationSeconds', 0):.1f}s")
    st.dataframe(
        [
            {
                "script": item.get("script"),
                "status": "passed" if item.get("returncode") == 0 else "failed",
                "exitCode": item.get("returncode"),
                "durationSeconds": f"{item.get('durationSeconds', 0):.1f}",
            }
            for item in data.get("results", [])
        ],
        width="stretch",
        hide_index=True,
    )


def _render_quick_agents(
    summary: dict[str, Any],
    maintenance: dict[str, Any],
    requirements: dict[str, Any],
    chaos: dict[str, Any],
) -> None:
    result_summary = summary.get("summary", {})
    cols = st.columns(5)
    cols[0].metric("Total", _num(result_summary.get("total")))
    cols[1].metric("Passed", _num(result_summary.get("passed")))
    cols[2].metric("Failed", _num(result_summary.get("failed")))
    cols[3].metric("Findings", _num(maintenance.get("total", summary.get("findingCount"))))
    cols[4].metric("Chaos Failed", _num(chaos.get("failed")))
    st.json({
        "requirementsStatus": requirements.get("status"),
        "confluence": summary.get("confluence"),
        "slack": summary.get("slack"),
        "grafana": summary.get("grafana"),
    })


def _render_quick_reporter(summary: dict[str, Any], weekly: dict[str, Any]) -> None:
    if not summary:
        st.info("No Python reporter summary is available yet.")
        return
    st.json({
        "summary": summary.get("summary"),
        "failureSummaries": summary.get("failureSummaries", []),
        "weeklyHtml": weekly.get("htmlPath"),
        "weeklyPdf": weekly.get("pdfPath"),
    })


def _render_quick_slack(summary: dict[str, Any], slack: dict[str, Any]) -> None:
    st.json({
        "digest": summary.get("slack", {}),
        "notifications": slack,
    })
    slack_url = _configured_url("SLACK_CHANNEL_URL") or SLACK_CHANNEL_URL
    if slack_url:
        st.link_button("Open Slack Channel", slack_url, width="stretch")
    else:
        st.caption("Slack webhooks do not provide a readable message URL. Set SLACK_CHANNEL_URL to show an Open Slack Channel button.")


def _render_quick_confluence(summary: dict[str, Any]) -> None:
    confluence = summary.get("confluence", {})
    st.json(confluence)
    page_url = _confluence_page_url(confluence)
    if page_url:
        st.link_button("Open Confluence Report", page_url, width="stretch")
    else:
        st.caption("Configure CONFLUENCE_BASE_URL and CONFLUENCE_PAGE_ID to open the report page from this dashboard.")


def _render_quick_grafana(summary: dict[str, Any]) -> None:
    grafana = summary.get("grafana", {})
    st.json(grafana)
    st.link_button("Open Grafana Dashboard", _grafana_dashboard_url(), width="stretch")


def _render_main_execution_progress(latest_run: dict[str, Any]) -> None:
    st.markdown('<div class="section-title">Live Execution Progress</div>', unsafe_allow_html=True)
    stages = latest_run.get("stages", []) if latest_run else []

    if not stages:
        st.markdown(
            """
            <div class="progress-empty">
              No execution flow yet. Select a Playwright script and click <strong>Run Playwright Flow</strong>.
            </div>
            """,
            unsafe_allow_html=True,
        )
        return

    st.markdown(_stage_progress_board_html(stages), unsafe_allow_html=True)
    created_at = latest_run.get("createdAt", "")
    if created_at:
        st.caption(f"Latest saved run: {created_at}")


def _render_overview(
    summary: dict[str, Any],
    maintenance: dict[str, Any],
    requirements: dict[str, Any],
    weekly: dict[str, Any],
    chaos: dict[str, Any],
    slack: dict[str, Any],
) -> None:
    result_summary = summary.get("summary", {})
    st.markdown('<div class="section-title">Latest Quality Snapshot</div>', unsafe_allow_html=True)
    cols = st.columns(6)
    cols[0].metric("Total", _num(result_summary.get("total")))
    cols[1].metric("Passed", _num(result_summary.get("passed")))
    cols[2].metric("Failed", _num(result_summary.get("failed")))
    cols[3].metric("Skipped", _num(result_summary.get("skipped")))
    cols[4].metric("Findings", _num(maintenance.get("total", summary.get("findingCount"))))
    cols[5].metric("Pass Rate", _percent(result_summary.get("passRate")))

    cols = st.columns(5)
    _status_panel(cols[0], "Confluence", summary.get("confluence", {}))
    _status_panel(cols[1], "Slack", summary.get("slack", {}))
    _status_panel(cols[2], "Grafana", summary.get("grafana", {}).get("pushgateway", summary.get("grafana", {})))
    _status_panel(cols[3], "Requirements", requirements)
    _status_panel(cols[4], "Chaos", chaos)

    with st.expander("Latest run metadata", expanded=False):
        st.json({
            "weeklyStatus": weekly.get("status"),
            "slackNotifications": slack,
            "createdAt": summary.get("createdAt") or maintenance.get("createdAt") or requirements.get("createdAt"),
        })


def _render_playwright_runs(
    scripts: dict[str, str],
    latest_run: dict[str, Any],
    env_name: str,
    result_globs: str,
) -> None:
    st.subheader("Playwright Script Execution")
    st.caption("Use the sidebar Run Controls to execute one Playwright script or one agent at a time.")

    if not scripts:
        st.warning("No Playwright test scripts were found in package.json.")
        return

    preview_rows = [
        {
            "script": name,
            "type": _script_type(command),
            "interactive": "yes" if _is_interactive_script(command) else "no",
            "command": command,
        }
        for name, command in scripts.items()
    ]
    with st.expander("Available Playwright scripts", expanded=False):
        st.dataframe(preview_rows, width="stretch", hide_index=True)

    if latest_run:
        st.markdown("**Latest dashboard-triggered Playwright run**")
        _render_playwright_run_result(latest_run, compact=True)
    else:
        st.info("No Playwright run has been started from the dashboard yet.")


def _render_playwright_run_result(data: dict[str, Any], compact: bool = False) -> None:
    total = data.get("total", 0)
    failed = data.get("failed", 0)
    passed = data.get("passed", 0)
    cols = st.columns(4)
    cols[0].metric("Scripts", total)
    cols[1].metric("Passed", passed)
    cols[2].metric("Failed", failed)
    cols[3].metric("Duration", f"{data.get('durationSeconds', 0):.1f}s")

    if failed:
        st.error("One or more Playwright scripts failed.")
    elif total:
        st.success("All selected Playwright scripts passed.")

    rows = [
        {
            "script": item.get("script"),
            "status": "passed" if item.get("returncode") == 0 else "failed",
            "exitCode": item.get("returncode"),
            "durationSeconds": f"{item.get('durationSeconds', 0):.1f}",
        }
        for item in data.get("results", [])
    ]
    if rows:
        st.dataframe(rows, width="stretch", hide_index=True)

    if data.get("stages"):
        st.markdown("**Execution flow**")
        st.markdown(_stage_progress_board_html(data["stages"], compact=True), unsafe_allow_html=True)

    if compact:
        return

    for item in data.get("results", []):
        status = "passed" if item.get("returncode") == 0 else "failed"
        with st.expander(f"{item.get('script')} - {status}", expanded=item.get("returncode") != 0):
            st.code(item.get("command", ""), language="powershell")
            if item.get("stdout"):
                st.text_area(f"{item.get('script')} stdout", item["stdout"], height=180)
            if item.get("stderr"):
                st.text_area(f"{item.get('script')} stderr", item["stderr"], height=180)

    post_run = data.get("postRun", {})
    post_result = post_run.get("result")
    if post_result:
        with st.expander(f"Post-run agent: {post_run.get('label')}", expanded=False):
            st.code(post_result.get("command", ""), language="powershell")
            if post_result.get("stdout"):
                st.text_area("post-run stdout", post_result["stdout"], height=160)
            if post_result.get("stderr"):
                st.text_area("post-run stderr", post_result["stderr"], height=160)


def _render_maintenance(data: dict[str, Any]) -> None:
    st.subheader("Maintenance Findings")
    st.caption("Enterprise readiness, dependency health, coverage drift, dead tests, and duplicate tests.")
    findings = data.get("findings", [])

    if not findings:
        st.info("No maintenance findings are available yet. Run Maintenance or Full Flow.")
        return

    severity_counts: dict[str, int] = {}
    for item in findings:
        severity = item.get("severity", "unknown")
        severity_counts[severity] = severity_counts.get(severity, 0) + 1
    st.markdown(
        " ".join(
            f'<span class="severity-chip severity-{key}">{key}: {value}</span>'
            for key, value in sorted(severity_counts.items())
        ),
        unsafe_allow_html=True,
    )

    rows = [
        {
            "severity": item.get("severity"),
            "type": item.get("type"),
            "message": item.get("message"),
            "payload": json.dumps(item.get("payload", {}), ensure_ascii=False),
        }
        for item in findings
    ]
    st.dataframe(rows, width="stretch", hide_index=True)


def _render_requirements(data: dict[str, Any]) -> None:
    st.subheader("Requirements Drift")
    if not data:
        st.info("No requirements drift output is available yet.")
        return

    cols = st.columns(4)
    cols[0].metric("Status", data.get("status", "unknown"))
    cols[1].metric("Snapshots", _num(data.get("snapshotCount")))
    cols[2].metric("Drift Items", _num(len(data.get("driftItems", []))))
    cols[3].metric("Skipped Links", _num(data.get("skippedCount")))

    drift_items = data.get("driftItems", [])
    if drift_items:
        st.markdown("**Updated Acceptance Criteria**")
        st.dataframe(
            [
                {
                    "jira": item.get("jiraKey"),
                    "storyLink": item.get("issueUrl"),
                    "summary": item.get("summary"),
                    "linkedTests": ", ".join(item.get("linkedTests", [])),
                    "acStatus": item.get("acceptanceCriteriaChanges", {}).get("status"),
                    "message": item.get("acceptanceCriteriaChanges", {}).get("message"),
                }
                for item in drift_items
            ],
            width="stretch",
            hide_index=True,
        )
    else:
        st.success("No acceptance-criteria drift detected in the latest run.")

    skipped = data.get("skippedItems", [])
    if skipped:
        with st.expander("Skipped Jira links", expanded=False):
            st.dataframe(skipped, width="stretch", hide_index=True)


def _render_reporting(summary: dict[str, Any], slack: dict[str, Any]) -> None:
    st.subheader("Reporting Integrations")
    if not summary:
        st.info("No reporting summary is available yet.")
        return

    rows = [
        _integration_row("Grafana Pushgateway", summary.get("grafana", {}).get("pushgateway", summary.get("grafana", {}))),
        _integration_row("Confluence", summary.get("confluence", {})),
        _integration_row("Slack Digest", summary.get("slack", {})),
    ]
    st.dataframe(rows, width="stretch", hide_index=True)

    if slack:
        st.markdown("**Slack notification breakdown**")
        st.json(slack)

    failure_summaries = summary.get("failureSummaries", [])
    if failure_summaries:
        st.markdown("**Failure summaries**")
        st.dataframe(failure_summaries, width="stretch", hide_index=True)
    else:
        st.success("No failure summaries in the latest reporting output.")


def _render_weekly_report(data: dict[str, Any]) -> None:
    st.subheader("Weekly Quality Scorecard")
    if not data:
        st.info("No weekly report has been generated yet.")
        return

    summary = data.get("summary", {})
    cols = st.columns(5)
    cols[0].metric("Total", _num(summary.get("total")))
    cols[1].metric("Passed", _num(summary.get("passed")))
    cols[2].metric("Failed", _num(summary.get("failed")))
    cols[3].metric("Skipped", _num(summary.get("skipped")))
    cols[4].metric("Pass Rate", _percent(summary.get("passRate")))

    st.markdown(
        f"""
        <div class="report-links">
          <strong>HTML:</strong> {data.get("htmlPath", "")}<br />
          <strong>PDF:</strong> {data.get("pdfPath", "")}
        </div>
        """,
        unsafe_allow_html=True,
    )

    cols = st.columns(2)
    _download_file(cols[0], "Download Latest HTML", data.get("latestHtmlPath") or data.get("htmlPath"), "text/html")
    _download_file(cols[1], "Download Latest PDF", data.get("latestPdfPath") or data.get("pdfPath"), "application/pdf")


def _render_chaos(data: dict[str, Any]) -> None:
    st.subheader("Chaos Checks")
    if not data:
        st.info("No chaos output is available yet.")
        return

    cols = st.columns(2)
    cols[0].metric("Scenarios", _num(data.get("total")))
    cols[1].metric("Failed", _num(data.get("failed")))
    st.dataframe(data.get("results", []), width="stretch", hide_index=True)


def _render_ollama_assistant(
    summary: dict[str, Any],
    maintenance: dict[str, Any],
    requirements: dict[str, Any],
    chaos: dict[str, Any],
) -> None:
    st.subheader("Ollama Assistant")
    st.caption("Optional local LLM helper. Start Ollama locally, then ask it to summarize your latest agent outputs.")

    cols = st.columns([1, 1])
    base_url = cols[0].text_input("Ollama base URL", value=os.environ.get("OLLAMA_BASE_URL", "http://localhost:11434"))
    model = cols[1].text_input("Model", value=os.environ.get("OLLAMA_MODEL", "llama3.1"))

    prompt = st.text_area(
        "Prompt",
        value=(
            "Summarize the latest automation quality status. "
            "Mention passed/failed tests, major maintenance findings, requirements drift, and recommended next actions."
        ),
        height=110,
    )

    context = {
        "agentSummary": summary,
        "maintenance": maintenance,
        "requirements": requirements,
        "chaos": chaos,
    }

    if st.button("Ask Ollama", type="primary", width="stretch"):
        with st.spinner("Asking local Ollama..."):
            response = _ask_ollama(base_url, model, prompt, context)
        if response["status"] == "ok":
            st.markdown("**LLM response**")
            st.write(response["text"])
        else:
            st.warning(response["message"])
            st.code("ollama serve\nollama pull llama3.1", language="powershell")

    with st.expander("Context sent to Ollama", expanded=False):
        st.json(context)


def _render_raw_outputs() -> None:
    st.subheader("Raw Agent Outputs")
    selected = st.selectbox("Output file", list(OUTPUT_FILES.keys()))
    path = ROOT / OUTPUT_FILES[selected]
    st.code(str(path.relative_to(ROOT)))

    if not path.exists():
        st.info("This output file does not exist yet.")
        return

    try:
        st.json(json.loads(path.read_text(encoding="utf-8")))
    except json.JSONDecodeError:
        st.text(path.read_text(encoding="utf-8"))


def _status_panel(column: Any, label: str, data: dict[str, Any]) -> None:
    status = _status_value(data)
    css_class = "ok" if status in {"sent", "updated", "completed", "generated", "ok", "no_drift", "passed"} else "warn"
    if label == "Chaos" and data.get("failed") == 0 and data.get("total"):
        status = "passed"
        css_class = "ok"
    column.markdown(
        f"""
        <div class="status-box">
          <div class="status-label">{label}</div>
          <div class="status-value {css_class}">{status or "not run"}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def _integration_row(name: str, data: dict[str, Any]) -> dict[str, Any]:
    return {
        "name": name,
        "status": data.get("status", "unknown"),
        "statusCode": data.get("statusCode"),
        "message": data.get("message"),
        "target": data.get("url") or data.get("pageId") or data.get("metricsPath"),
    }


def _download_file(column: Any, label: str, relative_path: str | None, mime: str) -> None:
    if not relative_path:
        column.info("No file path available.")
        return

    path = ROOT / relative_path
    if not path.exists():
        column.warning(f"Missing file: {relative_path}")
        return

    column.download_button(
        label,
        data=path.read_bytes(),
        file_name=path.name,
        mime=mime,
        width="stretch",
    )


def _available_environments() -> list[str]:
    discovered = []
    env_dir = ROOT / "env-files"
    if env_dir.exists():
        discovered = [
            path.name.removeprefix(".env.")
            for path in env_dir.glob(".env.*")
            if path.is_file()
            and not path.name.endswith(".example")
            and path.name != ".env"
            and path.name.removeprefix(".env.")
        ]

    ordered = [*DEFAULT_ENVIRONMENTS, *sorted(discovered)]
    seen: set[str] = set()
    return [item for item in ordered if not (item in seen or seen.add(item))]


def _environment_index(environments: list[str], preferred: str) -> int:
    return environments.index(preferred) if preferred in environments else 0


def _active_quick_view() -> str:
    value = st.query_params.get("quick", "")
    if isinstance(value, list):
        value = value[0] if value else ""
    allowed = {"playwright", "agents", "reporter", "slack", "confluence", "grafana"}
    return value if value in allowed else ""


def _configured_url(key: str) -> str:
    return os.environ.get(key, "").strip() or _env_file_value(key)


def _confluence_page_url(confluence: dict[str, Any]) -> str:
    configured_report_url = _configured_url("CONFLUENCE_REPORT_URL")
    if configured_report_url:
        return configured_report_url
    if CONFLUENCE_REPORT_URL:
        return CONFLUENCE_REPORT_URL

    base_url = _configured_url("CONFLUENCE_BASE_URL").rstrip("/")
    page_id = str(confluence.get("pageId") or _env_file_value("CONFLUENCE_PAGE_ID")).strip()
    if not base_url or not page_id:
        return CONFLUENCE_REPORT_URL

    if "/wiki" not in base_url:
        base_url = f"{base_url}/wiki"
    return f"{base_url}/pages/viewpage.action?pageId={page_id}"


def _grafana_dashboard_url() -> str:
    return _configured_url("GRAFANA_DASHBOARD_URL") or GRAFANA_DASHBOARD_URL


def _env_file_value(key: str) -> str:
    for env_name in _available_environments():
        env_path = ROOT / "env-files" / f".env.{env_name}"
        if not env_path.exists():
            continue
        for raw_line in env_path.read_text(encoding="utf-8").splitlines():
            line = raw_line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            item_key, item_value = line.split("=", 1)
            if item_key.strip() == key:
                return item_value.strip().strip('"').strip("'")
    return ""


def _playwright_scripts() -> dict[str, str]:
    package_json = _read_json("package.json", {})
    scripts = package_json.get("scripts", {})
    return {
        name: command
        for name, command in scripts.items()
        if isinstance(command, str) and _is_playwright_script(name, command)
    }


def _default_playwright_selection(scripts: dict[str, str]) -> list[str]:
    preferred = ["test_demo", "test:e2e"]
    for script in preferred:
        if script in scripts:
            return [script]
    return list(scripts.keys())[:1]


def _selected_script_index(scripts: dict[str, str], selected: str) -> int:
    names = list(scripts.keys())
    if selected in scripts:
        return names.index(selected)
    return 0


def _is_playwright_script(name: str, command: str) -> bool:
    return name.startswith("test_") or name.startswith("test:") or "playwright test" in command


def _is_interactive_script(command: str) -> bool:
    return "--ui" in command or "--headed" in command or "allure open" in command


def _script_type(command: str) -> str:
    if "--project=apiTest" in command:
        return "api"
    if "--ui" in command:
        return "ui mode"
    if "--headed" in command:
        return "headed"
    if "allure" in command:
        return "allure"
    return "headless"


def _run_npm_scripts(
    selected_scripts: list[str],
    scripts: dict[str, str],
    stop_on_failure: bool,
    timeout_seconds: int,
) -> dict[str, Any]:
    started = time.monotonic()
    results = []

    for script_name in selected_scripts:
        result = _run_npm_script(script_name, scripts[script_name], timeout_seconds)
        results.append(result)
        if stop_on_failure and result["returncode"] != 0:
            break

    failed = sum(1 for item in results if item["returncode"] != 0)
    return {
        "createdAt": datetime.now(timezone.utc).isoformat(),
        "selectedScripts": selected_scripts,
        "stopOnFailure": stop_on_failure,
        "total": len(results),
        "passed": len(results) - failed,
        "failed": failed,
        "durationSeconds": time.monotonic() - started,
        "results": results,
    }


def _build_execution_stages(
    selected_scripts: list[str],
    agent_stages: list[tuple[str, str]] | None = None,
) -> list[dict[str, Any]]:
    stages = [
        {
            "key": f"playwright:{script}",
            "label": _playwright_stage_label(script),
            "status": "pending",
            "progress": 0,
        }
        for script in selected_scripts
    ]
    active_agent_stages = AGENT_STAGE_DEFINITIONS if agent_stages is None else agent_stages
    stages.extend(
        {
            "key": key,
            "label": label,
            "status": "pending",
            "progress": 0,
        }
        for key, label in active_agent_stages
    )
    return stages


def _playwright_stage_label(script: str) -> str:
    if script == "test:e2e":
        return "Playwright E2E Flow"
    return f"Playwright {script}"


def _set_stage_status(stages: list[dict[str, Any]], key: str, status: str, progress: int | None = None) -> None:
    for stage in stages:
        if stage["key"] == key:
            stage["status"] = status
            if progress is not None:
                stage["progress"] = max(0, min(100, progress))
            elif status == "done":
                stage["progress"] = 100
            elif status == "failed":
                stage["progress"] = max(int(stage.get("progress", 0)), 100)
            elif status == "skipped":
                stage["progress"] = 0
            return


def _bump_running_stage(stages: list[dict[str, Any]], key: str, amount: int) -> None:
    for stage in stages:
        if stage["key"] == key and stage.get("status") == "running":
            current = int(stage.get("progress", 0))
            stage["progress"] = min(95, max(current + amount, current))
            return


def _skip_remaining_playwright_stages(stages: list[dict[str, Any]], selected_scripts: list[str], failed_script: str) -> None:
    should_skip = False
    for script in selected_scripts:
        if should_skip:
            _set_stage_status(stages, f"playwright:{script}", "skipped")
        if script == failed_script:
            should_skip = True


def _render_execution_monitor(
    stages: list[dict[str, Any]],
    progress_placeholder: Any,
    stage_placeholder: Any,
    current_placeholder: Any,
    current_label: str,
) -> None:
    percent = _overall_stage_percent(stages)
    running = next((stage for stage in stages if stage["status"] == "running"), None)
    running_label = running["label"] if running else current_label

    progress_placeholder.progress(
        percent,
        text=f"{percent}% complete | Current: {running_label}",
    )
    current_placeholder.markdown(
        f"""
        <div class="current-stage">
          <span>Currently running</span>
          <strong>{running_label} ({running.get("progress", 100) if running else percent}%)</strong>
        </div>
        """,
        unsafe_allow_html=True,
    )
    stage_placeholder.markdown(_stage_progress_board_html(stages), unsafe_allow_html=True)


def _overall_stage_percent(stages: list[dict[str, Any]]) -> int:
    if not stages:
        return 0
    return int(sum(int(stage.get("progress", 0)) for stage in stages) / len(stages))


def _stage_flow_html(stages: list[dict[str, Any]]) -> str:
    chips = []
    for stage in stages:
        status = stage.get("status", "pending")
        progress = int(stage.get("progress", 0))
        chips.append(
            f"""
            <span class="stage-chip stage-{status}">
              <span class="stage-dot"></span>{stage.get("label", "")} {progress}%
            </span>
            """
        )
    return f'<div class="stage-flow">{"".join(chips)}</div>'


def _stage_progress_board_html(stages: list[dict[str, Any]], compact: bool = False) -> str:
    cards = []
    for stage in stages:
        status = stage.get("status", "pending")
        progress = int(stage.get("progress", 0))
        links = _stage_extra_links(stage)
        cards.append(
            f"""
            <div class="stage-card stage-{status}">
              <div class="stage-card-top">
                <span>{stage.get("label", "")}</span>
                <strong>{progress}%</strong>
              </div>
              <div class="stage-bar"><div class="stage-fill" style="width:{progress}%"></div></div>
              <div class="stage-state">{status}</div>
              {links}
            </div>
            """
        )
    compact_class = " compact" if compact else ""
    return f'<div class="stage-progress-grid{compact_class}">{"".join(cards)}</div>'


def _stage_extra_links(stage: dict[str, Any]) -> str:
    if stage.get("key") != "allure:ports":
        return ""
    return """
      <div class="stage-links">
        <a href="http://localhost:5050" target="_blank">Open 5050</a>
        <a href="http://localhost:5051" target="_blank">Open 5051</a>
      </div>
    """


def _render_execution_output(output_placeholder: Any, source: str, line: str) -> None:
    if not line.strip():
        return
    output_placeholder.info(f"{source}: {line.strip()[:280]}")


def _agent_run_label(command: str | None) -> str:
    if command is None:
        return "Playwright Flow"
    labels = {
        "all": "All Agents",
        "normalize": "Normalize Results",
        "maintenance": "Maintenance Agent",
        "enterprise": "Enterprise Readiness Agent",
        "requirements": "Drift Agent",
        "reporting": "Reporting Agent",
        "jira-check": "Jira Check Agent",
        "weekly-pdf": "Weekly PDF Agent",
        "chaos": "Chaos Agent",
    }
    return labels.get(command, command)


def _script_plan_text(script_name: str, scripts: dict[str, str]) -> str:
    command = scripts.get(script_name, "")
    return "\n".join([
        f"1. npm run {script_name}",
        f"   {command}",
        "2. Optional: run selected single agent using Submit Agent",
        "3. Optional: run script + Reporting Agent",
    ])


def _run_npm_script_live(
    script_name: str,
    package_command: str,
    timeout_seconds: int,
    on_output,
) -> dict[str, Any]:
    npm = "npm.cmd" if os.name == "nt" else "npm"
    args = [npm, "run", script_name]
    result = _run_streamed_command(args, timeout_seconds, on_output)
    return {
        "script": script_name,
        "packageCommand": package_command,
        **result,
    }


def _run_agent_command_live(
    command: str,
    env_name: str,
    result_globs: str,
    stages: list[dict[str, Any]],
    progress_placeholder: Any,
    stage_placeholder: Any,
    current_placeholder: Any,
    output_placeholder: Any,
) -> dict[str, Any]:
    args = [
        sys.executable,
        "-m",
        "python_agents.cli",
        command,
        "--env",
        env_name,
        "--framework",
        "auto",
    ]
    globs = _parse_result_globs(result_globs)
    if globs:
        args.append("--results")
        args.extend(globs)

    def on_output(line: str) -> None:
        _bump_current_agent_stage(stages, 10)
        _update_agent_stages_from_output(line, stages)
        running = next((stage["label"] for stage in stages if stage["status"] == "running"), _agent_run_label(command))
        _render_execution_monitor(stages, progress_placeholder, stage_placeholder, current_placeholder, running)
        _render_execution_output(output_placeholder, f"agent:{command}", line)

    result = _run_streamed_command(args, 900, on_output, extra_env={"ENV_NAME": env_name})
    if result["returncode"] != 0:
        _fail_running_agent_stage(stages)
    else:
        for key, _label in AGENT_STAGE_BY_COMMAND.get(command, []):
            _set_stage_status(stages, key, "done")
    return result


def _bump_current_agent_stage(stages: list[dict[str, Any]], amount: int) -> None:
    for stage in stages:
        if stage["key"].startswith("agent:") and stage["status"] == "running":
            _bump_running_stage(stages, stage["key"], amount)
            return


def _update_agent_stages_from_output(line: str, stages: list[dict[str, Any]]) -> None:
    text = line.strip()
    transitions = [
        ("Normalized results written", "agent:normalize", "agent:maintenance"),
        ("Maintenance completed", "agent:maintenance", "agent:reporting"),
        ("Enterprise readiness completed", "agent:enterprise", None),
        ("Reporting Agent started", None, "agent:reporting"),
        ("Reporting Agent completed", "agent:reporting", "agent:requirements"),
        ("Reporting outputs written", "agent:reporting", "agent:requirements"),
        ("Requirements drift completed", "agent:requirements", "agent:jira"),
        ("Jira check completed", "agent:jira", "agent:weekly"),
        ("Weekly report generated", "agent:weekly", "agent:chaos"),
        ("Chaos checks completed", "agent:chaos", "allure:ports"),
    ]
    for marker, done_key, next_key in transitions:
        if marker in text:
            if done_key:
                _set_stage_status(stages, done_key, "done")
            if next_key:
                _set_stage_status(stages, next_key, "running", 5)
            return


def _fail_running_agent_stage(stages: list[dict[str, Any]]) -> None:
    for stage in stages:
        if stage["status"] == "running":
            _set_stage_status(stages, stage["key"], "failed")
            return


def _run_streamed_command(
    args: list[str],
    timeout_seconds: int,
    on_output,
    extra_env: dict[str, str] | None = None,
) -> dict[str, Any]:
    started = time.monotonic()
    output_lines: list[str] = []
    line_queue: queue.Queue[str | None] = queue.Queue()
    env = {**os.environ.copy(), "PYTHONUTF8": "1", **(extra_env or {})}

    process = subprocess.Popen(
        args,
        cwd=ROOT,
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        bufsize=1,
    )

    def reader() -> None:
        assert process.stdout is not None
        for line in process.stdout:
            line_queue.put(line)
        line_queue.put(None)

    thread = threading.Thread(target=reader, daemon=True)
    thread.start()
    timed_out = False
    reader_done = False

    while not reader_done:
        if time.monotonic() - started > timeout_seconds:
            timed_out = True
            process.kill()
            break
        try:
            line = line_queue.get(timeout=0.2)
        except queue.Empty:
            if process.poll() is not None and line_queue.empty():
                break
            continue
        if line is None:
            reader_done = True
            continue
        output_lines.append(line)
        on_output(line)

    returncode = process.wait(timeout=5)
    if timed_out:
        returncode = 124

    return {
        "command": _display_command(args),
        "returncode": returncode,
        "durationSeconds": time.monotonic() - started,
        "stdout": "".join(output_lines),
        "stderr": f"Timed out after {timeout_seconds} seconds." if timed_out else "",
    }


def _run_npm_script(script_name: str, package_command: str, timeout_seconds: int) -> dict[str, Any]:
    npm = "npm.cmd" if os.name == "nt" else "npm"
    args = [npm, "run", script_name]
    started = time.monotonic()

    try:
        completed = subprocess.run(
            args,
            cwd=ROOT,
            env={**os.environ.copy(), "PYTHONUTF8": "1"},
            text=True,
            capture_output=True,
            timeout=timeout_seconds,
            check=False,
        )
        return {
            "script": script_name,
            "packageCommand": package_command,
            "command": _display_command(args),
            "returncode": completed.returncode,
            "durationSeconds": time.monotonic() - started,
            "stdout": completed.stdout,
            "stderr": completed.stderr,
        }
    except subprocess.TimeoutExpired as error:
        return {
            "script": script_name,
            "packageCommand": package_command,
            "command": _display_command(args),
            "returncode": 124,
            "durationSeconds": time.monotonic() - started,
            "stdout": error.stdout or "",
            "stderr": f"Timed out after {timeout_seconds} seconds.",
        }


def _read_json(relative_path: str, fallback: Any) -> Any:
    path = ROOT / relative_path
    if not path.exists():
        return fallback
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return fallback


def _write_json(relative_path: str, data: Any) -> None:
    path = ROOT / relative_path
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2), encoding="utf-8")


def _ask_ollama(base_url: str, model: str, prompt: str, context: dict[str, Any]) -> dict[str, str]:
    url = f"{base_url.rstrip('/')}/api/generate"
    body = {
        "model": model,
        "prompt": f"{prompt}\n\nAgent context JSON:\n{json.dumps(context, indent=2)}",
        "stream": False,
    }
    request = urllib.request.Request(
        url,
        data=json.dumps(body).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )

    try:
        with urllib.request.urlopen(request, timeout=120) as response:
            payload = json.loads(response.read().decode("utf-8"))
            return {"status": "ok", "text": payload.get("response", "")}
    except (urllib.error.URLError, TimeoutError, json.JSONDecodeError, OSError) as error:
        return {
            "status": "error",
            "message": f"Ollama is not reachable at {base_url} with model {model}: {error}",
        }


def _parse_result_globs(value: str) -> list[str]:
    raw_items = value.replace(",", "\n").splitlines()
    return [item.strip() for item in raw_items if item.strip()]


def _display_command(args: list[str]) -> str:
    return " ".join(f'"{item}"' if " " in item else item for item in args)


def _num(value: Any) -> str:
    if value is None:
        return "0"
    return str(value)


def _percent(value: Any) -> str:
    try:
        return f"{float(value) * 100:.2f}%"
    except (TypeError, ValueError):
        return "0.00%"


def _status_value(data: dict[str, Any]) -> str:
    if not data:
        return ""
    if data.get("status"):
        return str(data["status"])
    if data.get("failed") == 0 and data.get("total"):
        return "passed"
    return "unknown"


def _inject_styles() -> None:
    st.markdown(
        """
        <style>
          :root {
            --ink: #182230;
            --muted: #5d6b82;
            --line: #d9e2ec;
            --blue: #2563eb;
            --green: #138a36;
            --red: #d1242f;
            --amber: #b7791f;
            --panel: #ffffff;
            --soft-blue: #eef5ff;
            --soft-green: #edfdf3;
            --soft-red: #fff1f2;
            --soft-amber: #fff8e6;
          }
          .stApp {
            background:
              linear-gradient(180deg, #eef5ff 0, #f7f9fc 260px, #f7f9fc 100%);
            color: var(--ink);
          }
          .block-container {
            padding-top: 1.4rem;
            padding-bottom: 2rem;
          }
          section[data-testid="stSidebar"] {
            background: #111827;
            border-right: 1px solid #243044;
          }
          section[data-testid="stSidebar"] h1,
          section[data-testid="stSidebar"] h2,
          section[data-testid="stSidebar"] h3,
          section[data-testid="stSidebar"] label,
          section[data-testid="stSidebar"] p,
          section[data-testid="stSidebar"] .stMarkdown {
            color: #f8fafc;
          }
          section[data-testid="stSidebar"] input,
          section[data-testid="stSidebar"] textarea,
          section[data-testid="stSidebar"] [data-baseweb="select"] * {
            color: #111827 !important;
          }
          section[data-testid="stSidebar"] div.stButton > button,
          section[data-testid="stSidebar"] div.stDownloadButton > button {
            background: #dbeafe !important;
            border: 1px solid #93c5fd !important;
            color: #0f172a !important;
            font-weight: 850 !important;
          }
          section[data-testid="stSidebar"] div.stButton > button *,
          section[data-testid="stSidebar"] div.stDownloadButton > button * {
            color: #0f172a !important;
            font-weight: 850 !important;
          }
          section[data-testid="stSidebar"] div.stButton > button[kind="primary"] {
            background: linear-gradient(90deg, #2563eb, #16a34a) !important;
            border: 0;
            color: #ffffff !important;
          }
          section[data-testid="stSidebar"] div.stButton > button[kind="primary"] *,
          section[data-testid="stSidebar"] div.stButton > button[data-testid="baseButton-primary"] * {
            color: #ffffff !important;
            font-weight: 900 !important;
          }
          section[data-testid="stSidebar"] div.stButton > button:hover,
          section[data-testid="stSidebar"] div.stDownloadButton > button:hover {
            background: #bfdbfe !important;
            border-color: #60a5fa !important;
          }
          section[data-testid="stSidebar"] div.stButton > button[kind="primary"]:hover {
            background: linear-gradient(90deg, #1d4ed8, #15803d) !important;
          }
          section[data-testid="stSidebar"] a[href*="localhost:3000"],
          section[data-testid="stSidebar"] div[data-testid="stLinkButton"] a,
          section[data-testid="stSidebar"] a[data-testid="stLinkButton"] {
            display: inline-flex !important;
            align-items: center !important;
            justify-content: center !important;
            width: 100% !important;
            min-height: 2.4rem !important;
            border-radius: 6px !important;
            background: #ffedd5 !important;
            border: 1px solid #fdba74 !important;
            color: #7c2d12 !important;
            font-weight: 900 !important;
            text-decoration: none !important;
          }
          section[data-testid="stSidebar"] a[href*="localhost:3000"] *,
          section[data-testid="stSidebar"] div[data-testid="stLinkButton"] a *,
          section[data-testid="stSidebar"] a[data-testid="stLinkButton"] * {
            color: #7c2d12 !important;
            font-weight: 900 !important;
          }
          section[data-testid="stSidebar"] a[href*="localhost:3000"]:hover,
          section[data-testid="stSidebar"] div[data-testid="stLinkButton"] a:hover,
          section[data-testid="stSidebar"] a[data-testid="stLinkButton"]:hover {
            background: #fed7aa !important;
            border-color: #fb923c !important;
            color: #7c2d12 !important;
            text-decoration: none !important;
          }
          section[data-testid="stSidebar"] a {
            color: #dbeafe !important;
          }
          .app-hero {
            display: flex;
            align-items: flex-end;
            justify-content: space-between;
            gap: 24px;
            border: 1px solid #c7d7f2;
            border-radius: 8px;
            padding: 22px 24px;
            margin-bottom: 18px;
            background:
              linear-gradient(135deg, rgba(37, 99, 235, 0.96), rgba(20, 184, 166, 0.88)),
              linear-gradient(90deg, #2563eb, #16a34a);
            box-shadow: 0 16px 40px rgba(15, 23, 42, 0.12);
          }
          .app-hero h1 {
            color: #ffffff;
            font-size: 2.1rem;
            line-height: 1.05;
            margin: 4px 0 8px;
            letter-spacing: 0;
          }
          .app-hero p,
          .hero-kicker {
            color: #eaf2ff;
            margin: 0;
          }
          .hero-kicker {
            font-size: 0.78rem;
            font-weight: 700;
            text-transform: uppercase;
          }
          .hero-badges {
            display: flex;
            flex-wrap: wrap;
            justify-content: flex-end;
            gap: 8px;
            max-width: 360px;
          }
          .badge,
          .severity-chip {
            display: inline-flex;
            align-items: center;
            border-radius: 999px;
            padding: 5px 10px;
            font-size: 0.78rem;
            font-weight: 700;
            margin: 0 6px 8px 0;
          }
          a.badge {
            text-decoration: none;
            box-shadow: 0 6px 16px rgba(15, 23, 42, 0.16);
            transition: transform 120ms ease, box-shadow 120ms ease;
          }
          a.badge:hover {
            transform: translateY(-1px);
            box-shadow: 0 10px 24px rgba(15, 23, 42, 0.22);
            text-decoration: none;
          }
          .badge.blue { background: #dbeafe; color: #1d4ed8; }
          .badge.green { background: #dcfce7; color: #166534; }
          .badge.red { background: #fee2e2; color: #b91c1c; }
          .badge.amber { background: #fef3c7; color: #92400e; }
          .badge.violet { background: #ede9fe; color: #6d28d9; }
          .badge.teal { background: #ccfbf1; color: #0f766e; }
          .badge.dark { background: #111827; color: #ffffff; border: 1px solid #374151; }
          .github-mark {
            display: inline-flex;
            align-items: center;
            justify-content: center;
            width: 22px;
            height: 22px;
            border-radius: 50%;
            background: #ffffff;
            color: #111827;
            font-size: 0.65rem;
            font-weight: 900;
            margin-right: 3px;
          }
          .quick-panel {
            border: 1px solid #c7d7f2;
            border-radius: 8px;
            background: #ffffff;
            padding: 16px;
            margin: 0 0 18px;
            box-shadow: 0 10px 28px rgba(15, 23, 42, 0.08);
          }
          .quick-title {
            color: var(--ink);
            font-size: 1.15rem;
            font-weight: 850;
            margin-bottom: 10px;
          }
          .quick-caption {
            color: var(--muted);
            font-size: 0.9rem;
          }
          .current-stage {
            display: flex;
            align-items: center;
            justify-content: space-between;
            gap: 12px;
            border: 1px solid #c7d7f2;
            border-radius: 8px;
            background: #f8fbff;
            padding: 10px 12px;
            margin: 8px 0;
          }
          .current-stage span {
            color: var(--muted);
            font-size: 0.82rem;
            font-weight: 700;
            text-transform: uppercase;
          }
          .current-stage strong {
            color: var(--blue);
            overflow-wrap: anywhere;
          }
          .stage-flow {
            display: flex;
            flex-wrap: wrap;
            gap: 8px;
            margin: 10px 0 16px;
          }
          .stage-chip {
            display: inline-flex;
            align-items: center;
            gap: 7px;
            border: 1px solid var(--line);
            border-radius: 999px;
            background: #ffffff;
            color: #475569;
            padding: 7px 11px;
            font-size: 0.82rem;
            font-weight: 800;
          }
          .stage-dot {
            width: 8px;
            height: 8px;
            border-radius: 50%;
            background: #94a3b8;
          }
          .stage-chip.stage-running {
            border-color: #bfdbfe;
            background: var(--soft-blue);
            color: var(--blue);
          }
          .stage-chip.stage-running .stage-dot {
            background: var(--blue);
          }
          .stage-chip.stage-done {
            border-color: #bbf7d0;
            background: var(--soft-green);
            color: var(--green);
          }
          .stage-chip.stage-done .stage-dot {
            background: var(--green);
          }
          .stage-chip.stage-failed {
            border-color: #fecdd3;
            background: var(--soft-red);
            color: var(--red);
          }
          .stage-chip.stage-failed .stage-dot {
            background: var(--red);
          }
          .stage-chip.stage-skipped {
            border-color: #fde68a;
            background: var(--soft-amber);
            color: var(--amber);
          }
          .stage-chip.stage-skipped .stage-dot {
            background: var(--amber);
          }
          .stage-progress-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
            gap: 10px;
            margin: 8px 0 18px;
          }
          .stage-progress-grid.compact {
            grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
          }
          .stage-card {
            border: 1px solid var(--line);
            border-radius: 8px;
            background: #ffffff;
            padding: 12px;
            box-shadow: 0 8px 24px rgba(15, 23, 42, 0.06);
          }
          .stage-card-top {
            display: flex;
            align-items: flex-start;
            justify-content: space-between;
            gap: 10px;
            color: var(--ink);
            font-size: 0.88rem;
            font-weight: 800;
            margin-bottom: 9px;
          }
          .stage-card-top span {
            overflow-wrap: anywhere;
          }
          .stage-card-top strong {
            font-size: 1rem;
          }
          .stage-bar {
            width: 100%;
            height: 9px;
            border-radius: 999px;
            background: #e5e7eb;
            overflow: hidden;
          }
          .stage-fill {
            height: 100%;
            border-radius: 999px;
            background: #94a3b8;
            transition: width 180ms ease;
          }
          .stage-state {
            margin-top: 7px;
            color: var(--muted);
            font-size: 0.75rem;
            font-weight: 800;
            text-transform: uppercase;
          }
          .stage-links {
            display: flex;
            flex-wrap: wrap;
            gap: 6px;
            margin-top: 10px;
          }
          .stage-links a {
            border: 1px solid #c7d7f2;
            border-radius: 999px;
            background: #ffffff;
            color: var(--blue);
            padding: 4px 8px;
            font-size: 0.75rem;
            font-weight: 800;
            text-decoration: none;
          }
          .stage-links a:hover {
            background: var(--soft-blue);
            text-decoration: none;
          }
          .stage-card.stage-running {
            border-color: #bfdbfe;
            background: var(--soft-blue);
          }
          .stage-card.stage-running .stage-fill {
            background: var(--blue);
          }
          .stage-card.stage-running .stage-card-top strong,
          .stage-card.stage-running .stage-state {
            color: var(--blue);
          }
          .stage-card.stage-done {
            border-color: #bbf7d0;
            background: var(--soft-green);
          }
          .stage-card.stage-done .stage-fill {
            background: var(--green);
          }
          .stage-card.stage-done .stage-card-top strong,
          .stage-card.stage-done .stage-state {
            color: var(--green);
          }
          .stage-card.stage-failed {
            border-color: #fecdd3;
            background: var(--soft-red);
          }
          .stage-card.stage-failed .stage-fill {
            background: var(--red);
          }
          .stage-card.stage-failed .stage-card-top strong,
          .stage-card.stage-failed .stage-state {
            color: var(--red);
          }
          .stage-card.stage-skipped {
            border-color: #fde68a;
            background: var(--soft-amber);
          }
          .stage-card.stage-skipped .stage-fill {
            background: var(--amber);
          }
          .stage-card.stage-skipped .stage-card-top strong,
          .stage-card.stage-skipped .stage-state {
            color: var(--amber);
          }
          .progress-empty {
            border: 1px dashed #c7d7f2;
            border-radius: 8px;
            background: #ffffff;
            color: var(--muted);
            padding: 14px;
            margin-bottom: 16px;
          }
          .section-title {
            color: var(--ink);
            font-size: 1.05rem;
            font-weight: 800;
            margin: 6px 0 12px;
          }
          div[data-testid="stMetric"] {
            border: 1px solid var(--line);
            border-radius: 6px;
            padding: 12px;
            background: var(--panel);
            box-shadow: 0 8px 24px rgba(15, 23, 42, 0.06);
          }
          .status-box {
            border: 1px solid var(--line);
            border-radius: 6px;
            padding: 12px;
            background: var(--panel);
            min-height: 78px;
            box-shadow: 0 8px 24px rgba(15, 23, 42, 0.06);
          }
          .status-label {
            color: var(--muted);
            font-size: 0.85rem;
            margin-bottom: 8px;
          }
          .status-value {
            font-size: 1.1rem;
            font-weight: 700;
            overflow-wrap: anywhere;
          }
          .status-value.ok {
            color: var(--green);
          }
          .status-value.warn {
            color: var(--amber);
          }
          .report-links {
            color: var(--red);
            border: 1px solid #ffebe9;
            border-radius: 6px;
            padding: 12px;
            background: var(--soft-red);
            margin: 12px 0;
            overflow-wrap: anywhere;
          }
          .severity-chip.severity-high {
            background: var(--soft-red);
            color: var(--red);
            border: 1px solid #ffc9cf;
          }
          .severity-chip.severity-medium {
            background: var(--soft-amber);
            color: var(--amber);
            border: 1px solid #ffe1a3;
          }
          .severity-chip.severity-low {
            background: var(--soft-blue);
            color: var(--blue);
            border: 1px solid #c7d7f2;
          }
          .severity-chip.severity-unknown {
            background: #f1f5f9;
            color: #475569;
            border: 1px solid #d9e2ec;
          }
          div.stButton > button[kind="primary"] {
            background: linear-gradient(90deg, #2563eb, #16a34a);
            border: 0;
            color: #ffffff !important;
            font-weight: 800;
          }
          div.stButton > button[kind="primary"] *,
          div.stButton > button[data-testid="baseButton-primary"] * {
            color: #ffffff !important;
          }
          div.stButton > button {
            border-radius: 6px;
            color: #111827 !important;
            font-weight: 700;
          }
          div.stButton > button * {
            color: inherit !important;
          }
          div[data-testid="stDataFrame"] {
            border-radius: 6px;
            overflow: hidden;
          }
        </style>
        """,
        unsafe_allow_html=True,
    )


if __name__ == "__main__":
    main()
