from __future__ import annotations

from ..shared.slack import send_slack_message
from ..shared.models import NormalizedTestResult


def send_daily_slack_digest(results: list[NormalizedTestResult], summaries: list[dict]) -> dict:
    total = len(results)
    passed = sum(1 for item in results if item.status == "passed")
    failed = sum(1 for item in results if item.status in {"failed", "timedOut"})
    skipped = sum(1 for item in results if item.status == "skipped")
    pass_rate = (passed / total * 100) if total else 0

    top_failures = "\n".join(
        f"- {item.get('testId')} - {item.get('classification')} - {item.get('owner')}"
        for item in summaries[:5]
    ) or "No failures"

    text = "\n".join([
        f"*Total:* {total}",
        f"*Passed:* {passed}",
        f"*Failed:* {failed}",
        f"*Skipped:* {skipped}",
        f"*Pass rate:* {pass_rate:.2f}%",
        "",
        "*Top failures:*",
        top_failures,
    ])
    return send_slack_message("Daily Playwright Quality Digest", text)
