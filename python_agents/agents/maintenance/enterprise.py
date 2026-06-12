from __future__ import annotations

import json
import subprocess
from pathlib import Path

from ..shared.io_utils import simple_yaml_quality_gates, write_json, write_text
from ..shared.metadata import missing_metadata
from ..shared.models import Finding, NormalizedTestResult
from ..shared.scanner import scan_test_declarations


REQUIRED_FILES = [
    "README.md",
    ".gitignore",
    "package.json",
    "config/quality-gates.yml",
]


REQUIRED_IGNORES = [
    "node_modules/",
    "/test-results/",
    "/playwright-report/",
    "/reports/",
    "/agent-state/",
    "env-files/.env.*",
]


def run_enterprise_checks(results: list[NormalizedTestResult]) -> list[Finding]:
    quality_gates = simple_yaml_quality_gates("config/quality-gates.yml")
    maintenance = quality_gates.get("maintenance", {})
    required_metadata = maintenance.get("requireTestMetadata") or ["id", "feature", "owner", "jira"]
    max_skipped = int(maintenance.get("maxSkippedTests", 0))
    declarations = scan_test_declarations()

    findings: list[Finding] = []
    findings.extend(_metadata_findings(declarations, required_metadata))
    findings.extend(_focused_findings(declarations))
    findings.extend(_skipped_findings(declarations, max_skipped))
    findings.extend(_duplicate_result_ids(results))
    findings.extend(_required_file_findings())
    findings.extend(_gitignore_findings())
    findings.extend(_tracked_env_findings())

    write_json("agent-state/python-enterprise-readiness.json", {
        "total": len(findings),
        "findings": [finding.to_dict() for finding in findings],
    })

    return findings


def _metadata_findings(declarations, required_metadata: list[str]) -> list[Finding]:
    findings: list[Finding] = []
    for declaration in declarations:
        missing = missing_metadata(declaration.metadata_text or declaration.title, required_metadata)
        if missing:
            findings.append(Finding(
                type="metadata_gap",
                severity="high",
                message=f"Missing required metadata in {declaration.file}:{declaration.line}",
                payload={
                    "framework": declaration.framework,
                    "title": declaration.title,
                    "missing": missing,
                },
            ))
    return findings


def _focused_findings(declarations) -> list[Finding]:
    return [
        Finding(
            type="unsafe_test_focus",
            severity="high",
            message=f"Focused test found in {item.file}:{item.line}",
            payload={"title": item.title, "modifier": item.modifier},
        )
        for item in declarations
        if item.modifier == "only"
    ]


def _skipped_findings(declarations, max_skipped: int) -> list[Finding]:
    skipped = [item for item in declarations if item.modifier in {"skip", "fixme"}]
    if len(skipped) <= max_skipped:
        return []

    return [
        Finding(
            type="skipped_test",
            severity="medium",
            message=f"Skipped/fixme test exceeds limit in {item.file}:{item.line}",
            payload={"title": item.title, "modifier": item.modifier, "maxSkippedTests": max_skipped},
        )
        for item in skipped
    ]


def _duplicate_result_ids(results: list[NormalizedTestResult]) -> list[Finding]:
    by_id: dict[str, list[NormalizedTestResult]] = {}
    for result in results:
        if result.test_id.startswith("UNKNOWN-"):
            continue
        by_id.setdefault(result.test_id, []).append(result)

    return [
        Finding(
            type="duplicate_test_id",
            severity="high",
            message=f"Duplicate test id found: {test_id}",
            payload={"tests": [{"title": item.title, "file": item.file} for item in items]},
        )
        for test_id, items in by_id.items()
        if len(items) > 1
    ]


def _required_file_findings() -> list[Finding]:
    return [
        Finding(
            type="framework_hygiene",
            severity="medium",
            message=f"Required file is missing: {file_path}",
            payload={"file": file_path},
        )
        for file_path in REQUIRED_FILES
        if not Path(file_path).exists()
    ]


def _gitignore_findings() -> list[Finding]:
    gitignore = Path(".gitignore")
    if not gitignore.exists():
        return []

    text = gitignore.read_text(encoding="utf-8")
    return [
        Finding(
            type="framework_hygiene",
            severity="medium",
            message=f"Generated or sensitive path should be ignored: {entry}",
            payload={"entry": entry},
        )
        for entry in REQUIRED_IGNORES
        if entry not in text
    ]


def _tracked_env_findings() -> list[Finding]:
    safe_dir = str(Path.cwd()).replace("\\", "/")
    try:
        completed = subprocess.run(
            ["git", "-c", f"safe.directory={safe_dir}", "ls-files", "--", ".env", ".env.*", "env-files/.env.*"],
            check=True,
            capture_output=True,
            text=True,
        )
    except (FileNotFoundError, subprocess.CalledProcessError):
        return []

    tracked = [
        line.strip()
        for line in completed.stdout.splitlines()
        if line.strip() and not line.strip().endswith(".example")
    ]

    return [
        Finding(
            type="secret_hygiene",
            severity="high",
            message=f"Real environment file is tracked by Git: {file_path}",
            payload={"file": file_path},
        )
        for file_path in tracked
    ]


def result_summary(results: list[NormalizedTestResult]) -> dict:
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


def write_enterprise_markdown(results: list[NormalizedTestResult], findings: list[Finding]) -> None:
    summary = result_summary(results)
    lines = [
        "# Universal Automation Agent Report",
        "",
        "## Execution Summary",
        "",
        f"- Total: {summary['total']}",
        f"- Passed: {summary['passed']}",
        f"- Failed: {summary['failed']}",
        f"- Skipped: {summary['skipped']}",
        f"- Flaky: {summary['flaky']}",
        f"- Unknown: {summary['unknown']}",
        f"- Pass Rate: {summary['passRate']:.2%}",
        "",
        "## Enterprise Findings",
        "",
    ]

    if findings:
        for finding in findings:
            lines.append(f"- **{finding.severity.upper()}** {finding.type}: {finding.message}")
    else:
        lines.append("- No enterprise readiness findings.")

    write_text("reports/ai-summary/python-agent-report.md", "\n".join(lines) + "\n")
