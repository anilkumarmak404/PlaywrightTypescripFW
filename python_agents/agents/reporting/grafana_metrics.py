from __future__ import annotations

import os
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone

from ..shared.io_utils import write_text
from ..shared.models import NormalizedTestResult


def push_grafana_metrics(results: list[NormalizedTestResult]) -> dict:
    metrics = build_prometheus_metrics(results)
    written_path = write_text("reports/metrics/playwright.prom", metrics)
    push_result = _push_to_pushgateway(metrics)
    return {"status": "completed", "metricsPath": str(written_path), "pushgateway": push_result}


def build_prometheus_metrics(results: list[NormalizedTestResult]) -> str:
    summary = _summary(results)
    run_id = results[0].run_id if results else f"empty-{time.time_ns()}"
    latest_run_at = sorted(item.run_at for item in results if item.run_at)[-1] if any(item.run_at for item in results) else None
    run_started_at = _unix_seconds(latest_run_at)
    run_label = f'run_id="{_escape_label(run_id)}"'

    metrics = f"""
# HELP playwright_tests_total Total Playwright tests
# TYPE playwright_tests_total gauge
playwright_tests_total {summary['total']}

# HELP playwright_tests_passed Passed Playwright tests
# TYPE playwright_tests_passed gauge
playwright_tests_passed {summary['passed']}

# HELP playwright_tests_failed Failed Playwright tests
# TYPE playwright_tests_failed gauge
playwright_tests_failed {summary['failed']}

# HELP playwright_tests_skipped Skipped Playwright tests
# TYPE playwright_tests_skipped gauge
playwright_tests_skipped {summary['skipped']}

# HELP playwright_tests_flaky Flaky Playwright tests
# TYPE playwright_tests_flaky gauge
playwright_tests_flaky {summary['flaky']}

# HELP playwright_tests_unknown Unknown Playwright tests
# TYPE playwright_tests_unknown gauge
playwright_tests_unknown {summary['unknown']}

# HELP playwright_pass_rate Playwright pass rate
# TYPE playwright_pass_rate gauge
playwright_pass_rate {summary['passRate']}

# HELP playwright_run_info Playwright run marker. Value is always 1.
# TYPE playwright_run_info gauge
playwright_run_info{{{run_label}}} 1

# HELP playwright_run_started_at_seconds Playwright run timestamp in Unix seconds
# TYPE playwright_run_started_at_seconds gauge
playwright_run_started_at_seconds{{{run_label}}} {run_started_at}

# HELP playwright_run_tests_total Total tests for one Playwright run
# TYPE playwright_run_tests_total gauge
playwright_run_tests_total{{{run_label}}} {summary['total']}

# HELP playwright_run_tests_passed Passed tests for one Playwright run
# TYPE playwright_run_tests_passed gauge
playwright_run_tests_passed{{{run_label}}} {summary['passed']}

# HELP playwright_run_tests_failed Failed tests for one Playwright run
# TYPE playwright_run_tests_failed gauge
playwright_run_tests_failed{{{run_label}}} {summary['failed']}

# HELP playwright_run_tests_skipped Skipped tests for one Playwright run
# TYPE playwright_run_tests_skipped gauge
playwright_run_tests_skipped{{{run_label}}} {summary['skipped']}

# HELP playwright_run_tests_flaky Flaky tests for one Playwright run
# TYPE playwright_run_tests_flaky gauge
playwright_run_tests_flaky{{{run_label}}} {summary['flaky']}

# HELP playwright_run_tests_unknown Unknown tests for one Playwright run
# TYPE playwright_run_tests_unknown gauge
playwright_run_tests_unknown{{{run_label}}} {summary['unknown']}
"""
    return metrics.strip() + "\n"


def _push_to_pushgateway(metrics: str) -> dict:
    pushgateway_url = os.environ.get("PUSHGATEWAY_URL")
    if not pushgateway_url:
        return {"status": "skipped", "message": "PUSHGATEWAY_URL is not configured"}

    job = _encode_path_value(os.environ.get("PUSHGATEWAY_JOB") or "playwright-reporting")
    environment = _encode_path_value(os.environ.get("ENV_NAME") or "demo")
    url = f"{pushgateway_url.rstrip('/')}/metrics/job/{job}/environment/{environment}"
    request = urllib.request.Request(
        url,
        data=metrics.encode("utf-8"),
        method="PUT",
        headers={"Content-Type": "text/plain; version=0.0.4"},
    )

    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            return {"status": "sent", "statusCode": response.status, "url": url}
    except urllib.error.HTTPError as error:
        detail = error.read().decode("utf-8", errors="ignore")
        return {"status": "failed", "message": f"Pushgateway failed with {error.code}: {detail}", "url": url}
    except (urllib.error.URLError, OSError) as error:
        return {"status": "failed", "message": f"Pushgateway request failed: {error}", "url": url}


def _summary(results: list[NormalizedTestResult]) -> dict:
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


def _escape_label(value: str) -> str:
    return value.replace("\\", "\\\\").replace("\n", "\\n").replace('"', '\\"')


def _encode_path_value(value: str) -> str:
    return urllib.parse.quote("-".join(value.lower().split()), safe="")


def _unix_seconds(value: str | None) -> int:
    if not value:
        return int(time.time())
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return int(time.time())
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return int(parsed.timestamp())
