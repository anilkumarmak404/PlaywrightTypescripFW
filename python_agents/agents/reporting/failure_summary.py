from __future__ import annotations

from ..shared.models import NormalizedTestResult


def classify_failure(result: NormalizedTestResult) -> str:
    error = f"{result.error_message or ''}\n{result.stack or ''}".lower()

    if "timeout" in error or "timed out" in error:
        return "flaky"
    if "locator" in error or "strict mode violation" in error or "selector" in error:
        return "test_bug"
    if "500" in error or "api" in error or "network" in error:
        return "environment_issue"
    if "expect" in error or "assert" in error or "to be visible" in error or "to have text" in error:
        return "product_bug"
    return "unknown"


def summarize_failures(results: list[NormalizedTestResult]) -> list[dict]:
    summaries: list[dict] = []

    for failure in results:
        classification = classify_failure(failure)
        summaries.append({
            "testId": failure.test_id,
            "classification": classification,
            "owner": failure.owner,
            "summary": f"Test {failure.test_id} failed in feature {failure.feature}.",
            "probableCause": failure.error_message or "No error message captured.",
            "suggestedAction": _suggested_action(classification),
        })

    return summaries


def _suggested_action(classification: str) -> str:
    if classification == "test_bug":
        return "Review selector, locator, or test data."
    if classification == "environment_issue":
        return "Check service health, API response, network, or test environment."
    if classification == "flaky":
        return "Review timeout, wait condition, unstable data, or retry history."
    return "Review application behavior against expected result."
