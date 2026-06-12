from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any

from ..shared.io_utils import read_json
from ..shared.models import Finding, TestRegistryItem


def find_dead_tests(registry: list[TestRegistryItem], older_than_days: int = 30) -> list[Finding]:
    history = read_json("agent-state/test-history.json", [])
    cutoff = datetime.now(timezone.utc) - timedelta(days=older_than_days)

    findings: list[Finding] = []
    for test in registry:
        runs = [item for item in history if item.get("testId") == test.id]
        if not runs or _latest_run_at(runs) is None or _latest_run_at(runs) < cutoff:
            findings.append(Finding(
                type="dead_test",
                severity="medium",
                message=f"Test {test.id} has not run in {older_than_days}+ days",
                payload=test.to_dict(),
            ))

    return findings


def _latest_run_at(runs: list[dict[str, Any]]) -> datetime | None:
    parsed = [_parse_datetime(str(item.get("runAt") or "")) for item in runs]
    valid = [item for item in parsed if item is not None]
    return max(valid) if valid else None


def _parse_datetime(value: str) -> datetime | None:
    if not value:
        return None

    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None

    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)
