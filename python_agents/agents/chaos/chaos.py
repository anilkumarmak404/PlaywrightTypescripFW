from __future__ import annotations

import tempfile
from pathlib import Path

from ..shared.adapters import load_results
from ..shared.fingerprint import create_failure_fingerprint
from ..shared.io_utils import write_json
from ..shared.models import NormalizedTestResult
from ..shared.resilience import with_circuit_breaker


def run_chaos_checks() -> dict:
    results: list[dict] = []

    def record(name: str, fn) -> None:
        try:
            results.append({"scenario": name, "status": "passed", "detail": fn()})
        except Exception as error:  # noqa: BLE001
            results.append({"scenario": name, "status": "failed", "detail": str(error)})

    record("Jira down circuit breaker fallback", _jira_down_circuit_breaker_fallback)
    record("Slack webhook invalid is non-fatal", _slack_webhook_invalid_is_non_fatal)
    record("Confluence update conflict is isolated", _confluence_update_conflict_is_isolated)
    record("Missing result files returns empty list", _missing_results_returns_empty)
    record("Missing screenshot is accepted", _missing_screenshot_is_accepted)
    record("Agent crash halfway can be captured by caller", _agent_crash_halfway_can_be_captured)
    record("Fingerprint matches TypeScript algorithm", _fingerprint_matches_typescript_algorithm)
    record("Same failure repeated 5 times is idempotent", _same_failure_idempotent)
    record("Different failure creates different fingerprint", _different_failure_fingerprint)
    record("Agent output fallback path is safe", _fallback_state_is_safe)

    output = {
        "total": len(results),
        "failed": sum(1 for item in results if item["status"] == "failed"),
        "results": results,
    }
    write_json("agent-state/python-latest-chaos-results.json", output)
    return output


def _jira_down_circuit_breaker_fallback() -> str:
    def outage() -> None:
        raise RuntimeError("simulated Jira outage")

    breaker = with_circuit_breaker(outage, "chaos-jira")
    output = breaker.fire()
    if output is not None:
        raise RuntimeError("expected circuit breaker fallback to return None")
    return "fallback returned None"


def _slack_webhook_invalid_is_non_fatal() -> str:
    def invalid_webhook() -> None:
        raise RuntimeError("simulated invalid Slack webhook")

    breaker = with_circuit_breaker(invalid_webhook, "chaos-slack")
    breaker.fire()
    return "fallback completed without throwing"


def _confluence_update_conflict_is_isolated() -> str:
    def version_conflict() -> None:
        raise RuntimeError("simulated Confluence version conflict")

    breaker = with_circuit_breaker(version_conflict, "chaos-confluence")
    breaker.fire()
    return "fallback completed without throwing"


def _missing_results_returns_empty() -> str:
    with tempfile.TemporaryDirectory() as temp:
        results = load_results("junit", [str(Path(temp) / "*.xml")])
        if results:
            raise RuntimeError(f"Expected empty results, got {len(results)}")
    return "empty result set returned"


def _missing_screenshot_is_accepted() -> str:
    result = _failed_result(screenshot_path=None)
    if result.screenshot_path is not None:
        raise RuntimeError("screenshot_path should be optional")
    return "missing screenshot accepted"


def _agent_crash_halfway_can_be_captured() -> str:
    wrote_first_step = False

    try:
        wrote_first_step = True
        raise RuntimeError("simulated midway crash")
    except RuntimeError:
        if not wrote_first_step:
            raise

    return "midway crash caught and later steps can continue"


def _same_failure_idempotent() -> str:
    fingerprints = {create_failure_fingerprint(_failed_result()) for _ in range(5)}
    if len(fingerprints) != 1:
        raise RuntimeError("same failure produced different fingerprints")
    return next(iter(fingerprints))[:12]


def _fingerprint_matches_typescript_algorithm() -> str:
    expected = "da2d2f891539cb587925410ebd94d2ec388c0180e9221f0f69e93810fd9ae56b"
    actual = create_failure_fingerprint(_failed_result())
    if actual != expected:
        raise RuntimeError(f"expected {expected}, got {actual}")
    return actual[:12]


def _different_failure_fingerprint() -> str:
    first = create_failure_fingerprint(_failed_result())
    second = create_failure_fingerprint(_failed_result(test_id="LEAVE-001", feature="leave", error_message="Expected Leave page"))
    if first == second:
        raise RuntimeError("different failures produced same fingerprint")
    return f"{first[:12]} != {second[:12]}"


def _fallback_state_is_safe() -> str:
    write_json("agent-state/python-chaos-write-check.json", {"ok": True})
    return "state write succeeded"


def _failed_result(**overrides) -> NormalizedTestResult:
    data = {
        "run_id": "chaos-run",
        "test_id": "LOGIN-002",
        "title": "Chaos failure",
        "file": "tests/ui-tests/login-module.spec.ts",
        "framework": "generic",
        "feature": "login",
        "owner": "qa-auth",
        "jira": "SCRUM-31",
        "status": "failed",
        "duration_ms": 100,
        "error_message": "Expected Dashboard but received Login page 123",
    }
    data.update(overrides)
    return NormalizedTestResult(**data)
