from __future__ import annotations

import json
from pathlib import Path

from ..shared.metadata import extract_metadata
from ..shared.models import NormalizedTestResult


def parse_latest_agent_results() -> list[NormalizedTestResult]:
    path = Path("reports/ai-summary/latest-agent-results.json")
    if not path.exists():
        print(f"Missing {path}. Reporting agent will continue with zero test results.")
        return []

    data = json.loads(path.read_text(encoding="utf-8"))
    results = data.get("results", [])
    run_id = data.get("runId", "unknown-run")
    return [_from_agent_result(item, run_id) for item in results]


def _from_agent_result(item: dict, run_id: str) -> NormalizedTestResult:
    title = str(item.get("title") or item.get("testId") or "unknown")
    metadata = extract_metadata(title, str(item.get("file") or ""))
    return NormalizedTestResult(
        run_id=str(item.get("runId") or run_id),
        test_id=str(item.get("testId") or metadata.test_id),
        title=title,
        file=str(item.get("file") or ""),
        framework="playwright",
        feature=str(item.get("feature") or metadata.feature),
        owner=str(item.get("owner") or metadata.owner),
        jira=str(item.get("jira") or metadata.jira),
        status=_normalize_status(str(item.get("status") or "unknown")),
        duration_ms=int(item.get("durationMs") or 0),
        retry=int(item.get("retry") or 0),
        error_message=item.get("errorMessage"),
        stack=item.get("stack"),
        trace_path=item.get("tracePath"),
        screenshot_path=item.get("screenshotPath"),
        video_path=item.get("videoPath"),
        run_at=item.get("runAt"),
    )


def _normalize_status(status: str) -> str:
    if status == "timedOut":
        return "timedOut"
    value = status.lower()
    if value == "passed":
        return "passed"
    if value == "failed":
        return "failed"
    if value == "skipped":
        return "skipped"
    if value == "flaky":
        return "flaky"
    return "unknown"
