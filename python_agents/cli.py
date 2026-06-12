from __future__ import annotations

import argparse
import os

from .agents.chaos.chaos import run_chaos_checks
from .agents.maintenance.enterprise import run_enterprise_checks
from .agents.maintenance.index import run_maintenance_checks
from .agents.maintenance.requirements_drift import run_requirements_drift
from .agents.reporting.index import run_reporting_agent, write_normalized_results
from .agents.reporting.jira_client import check_jira_auth
from .agents.reporting.slack_client import (
    send_chaos_summary,
    send_enterprise_summary,
    send_jira_check_summary,
    send_maintenance_summary,
    send_requirements_summary,
    send_weekly_report_summary,
)
from .agents.reporting.weekly_report import generate_weekly_report
from .agents.shared.adapters import load_results
from .agents.shared.io_utils import load_env_file, write_json


def main() -> None:
    parser = argparse.ArgumentParser(description="Framework-neutral automation agents")
    parser.add_argument(
        "command",
        nargs="?",
        default="all",
        choices=[
            "normalize",
            "maintenance",
            "enterprise",
            "requirements",
            "jira-check",
            "reporting",
            "weekly-pdf",
            "chaos",
            "all",
        ],
        help="Agent command to run",
    )
    parser.add_argument(
        "--framework",
        default="auto",
        choices=["auto", "playwright", "playwright-agent", "junit", "selenium", "cypress", "pytest", "generic"],
        help="Input framework/result adapter",
    )
    parser.add_argument(
        "--results",
        nargs="*",
        help="Result file globs. If omitted, defaults are selected from --framework.",
    )
    parser.add_argument(
        "--env",
        default=None,
        help="Environment name. Loads env-files/.env.<name> when present.",
    )

    args = parser.parse_args()
    env_name = args.env or os.environ.get("ENV_NAME") or "demo"
    load_env_file(f"env-files/.env.{env_name}")

    results = load_results(framework=args.framework, result_paths=args.results)
    slack_notifications = {}

    if args.command in {"normalize", "all"}:
        write_normalized_results(results)
        print(f"Normalized results written. Tests: {len(results)}")

    findings = []
    if args.command in {"maintenance", "all"}:
        findings = run_maintenance_checks(results)
        print(f"Maintenance completed. Findings: {len(findings)}")
        slack_notifications["maintenance"] = send_maintenance_summary(findings)
    elif args.command == "enterprise":
        findings = run_enterprise_checks(results)
        print(f"Enterprise readiness completed. Findings: {len(findings)}")
        if args.command in {"enterprise", "all"}:
            slack_notifications["enterprise"] = send_enterprise_summary(findings)

    if args.command in {"reporting", "all"}:
        reporting_result = run_reporting_agent(results, findings)
        print(
            "Reporting outputs written. "
            f"Total: {reporting_result['total']}. Failures: {reporting_result['failures']}."
        )

    if args.command in {"requirements", "all"}:
        requirement_result = run_requirements_drift()
        print(
            "Requirements drift completed. "
            f"Status: {requirement_result['status']}. "
            f"Drift: {len(requirement_result['driftItems'])}. "
            f"Skipped: {requirement_result['skippedCount']}."
        )
        slack_notifications["requirements"] = send_requirements_summary(requirement_result)

    if args.command in {"jira-check", "all"}:
        jira_result = check_jira_auth()
        write_json("agent-state/python-jira-auth-check.json", jira_result)
        print(f"Jira check completed. Status: {jira_result['status']}")
        slack_notifications["jiraCheck"] = send_jira_check_summary(jira_result)

    if args.command in {"weekly-pdf", "all"}:
        weekly_result = generate_weekly_report(results)
        write_json("agent-state/python-weekly-report.json", weekly_result)
        print(f"Weekly report generated. HTML: {weekly_result['htmlPath']} PDF: {weekly_result['pdfPath']}")
        slack_notifications["weeklyReport"] = send_weekly_report_summary(weekly_result)

    if args.command in {"chaos", "all"}:
        chaos_result = run_chaos_checks()
        print(f"Chaos checks completed. Failed: {chaos_result['failed']} / {chaos_result['total']}")
        slack_notifications["chaos"] = send_chaos_summary(chaos_result)
        if slack_notifications:
            write_json("agent-state/python-slack-notifications.json", slack_notifications)
        if chaos_result["failed"]:
            raise SystemExit(1)

    if slack_notifications:
        write_json("agent-state/python-slack-notifications.json", slack_notifications)


if __name__ == "__main__":
    main()
