from __future__ import annotations

from datetime import datetime, timezone

from .coverage_drift import detect_coverage_drift
from .dead_tests import find_dead_tests
from .dependency_health import check_dependency_health
from .enterprise import run_enterprise_checks
from .redundant_tests import find_redundant_tests
from .scan_tests import scan_tests
from ..shared.io_utils import write_json
from ..shared.models import Finding, NormalizedTestResult


def run_maintenance_checks(results: list[NormalizedTestResult]) -> list[Finding]:
    registry = scan_tests("tests/**/*.spec.ts")
    findings = [
        *find_dead_tests(registry, 30),
        *detect_coverage_drift(registry),
        *run_enterprise_checks(results),
        *check_dependency_health(),
        *find_redundant_tests(registry),
    ]

    registry_output = [item.to_dict() for item in registry]
    findings_output = {
        "createdAt": datetime.now(timezone.utc).isoformat(),
        "total": len(findings),
        "findings": [finding.to_dict() for finding in findings],
    }

    write_json("agent-state/test-registry.json", registry_output)
    write_json("agent-state/python-test-registry.json", registry_output)
    write_json("agent-state/latest-maintenance-findings.json", findings_output)
    write_json("agent-state/python-latest-maintenance-findings.json", findings_output)

    return findings
