from __future__ import annotations

import fnmatch
import subprocess
from pathlib import Path
from typing import Any

from ..shared.models import Finding, TestRegistryItem


def detect_coverage_drift(registry: list[TestRegistryItem]) -> list[Finding]:
    feature_map = _load_feature_map("config/feature-map.yml")
    changed_files = _changed_files()
    findings: list[Finding] = []

    if not feature_map or not changed_files:
        return findings

    for feature_name, feature_config in feature_map.items():
        code_patterns = feature_config.get("code", [])
        test_patterns = feature_config.get("tests", [])
        changed_code = [
            file_path
            for file_path in changed_files
            if any(_matches(file_path, pattern) for pattern in code_patterns)
        ]

        if not changed_code:
            continue

        related_test_changed = any(
            _matches(file_path, pattern)
            for file_path in changed_files
            for pattern in test_patterns
        )
        existing_tests = [test for test in registry if test.feature == feature_name]

        if not related_test_changed or not existing_tests:
            findings.append(Finding(
                type="coverage_drift",
                severity="high",
                message=f"Code changed for feature {feature_name}, but no matching test update was found",
                payload={
                    "feature": feature_name,
                    "owner": feature_config.get("owner", "unknown"),
                    "changedCode": changed_code,
                    "existingTests": [test.id for test in existing_tests],
                },
            ))

    return findings


def _changed_files() -> list[str]:
    for args in (["diff", "--name-only", "origin/main...HEAD"], ["diff", "--name-only", "HEAD"]):
        output = _git(args)
        if output:
            return [_normalize_path(line) for line in output.splitlines() if line.strip()]
    return []


def _git(args: list[str]) -> str:
    safe_dir = str(Path.cwd()).replace("\\", "/")
    try:
        completed = subprocess.run(
            ["git", "-c", f"safe.directory={safe_dir}", *args],
            check=True,
            capture_output=True,
            text=True,
            timeout=30,
        )
    except (FileNotFoundError, subprocess.CalledProcessError, subprocess.TimeoutExpired):
        return ""
    return completed.stdout.strip()


def _load_feature_map(path: str) -> dict[str, dict[str, Any]]:
    target = Path(path)
    if not target.exists():
        return {}

    features: dict[str, dict[str, Any]] = {}
    current_feature: str | None = None
    current_list: str | None = None

    for raw_line in target.read_text(encoding="utf-8").splitlines():
        if not raw_line.strip() or raw_line.lstrip().startswith("#"):
            continue

        if raw_line.startswith("  ") and not raw_line.startswith("    ") and raw_line.rstrip().endswith(":"):
            current_feature = raw_line.strip()[:-1]
            features[current_feature] = {}
            current_list = None
            continue

        if not current_feature:
            continue

        stripped = raw_line.strip()
        if raw_line.startswith("    ") and not raw_line.startswith("      ") and ":" in stripped:
            key, value = stripped.split(":", 1)
            key = key.strip()
            value = value.strip()
            if value:
                features[current_feature][key] = value
                current_list = None
            else:
                features[current_feature][key] = []
                current_list = key
            continue

        if current_list and raw_line.startswith("      ") and stripped.startswith("- "):
            features[current_feature].setdefault(current_list, []).append(stripped[2:])

    return features


def _matches(file_path: str, pattern: str) -> bool:
    normalized_file = _normalize_path(file_path)
    normalized_pattern = _normalize_path(pattern)
    return fnmatch.fnmatch(normalized_file, normalized_pattern)


def _normalize_path(value: str) -> str:
    return value.strip().replace("\\", "/")
