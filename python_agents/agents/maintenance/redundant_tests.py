from __future__ import annotations

import re

from ..shared.models import Finding, TestRegistryItem


TAG_PATTERN = re.compile(r"@[a-zA-Z0-9-_:]+")


def find_redundant_tests(registry: list[TestRegistryItem]) -> list[Finding]:
    findings: list[Finding] = []
    by_feature: dict[str, list[TestRegistryItem]] = {}

    for test in registry:
        by_feature.setdefault(test.feature, []).append(test)

    for feature, tests in by_feature.items():
        seen: dict[str, list[TestRegistryItem]] = {}
        for test in tests:
            normalized = _normalize_title(test.title)
            seen.setdefault(normalized, []).append(test)

        for group in seen.values():
            if len(group) > 1:
                findings.append(Finding(
                    type="redundant_test",
                    severity="low",
                    message=f"Possible duplicate tests found in feature {feature}",
                    payload={
                        "feature": feature,
                        "tests": [
                            {
                                "id": item.id,
                                "file": item.file,
                                "title": item.title,
                            }
                            for item in group
                        ],
                    },
                ))

    return findings


def _normalize_title(title: str) -> str:
    without_tags = TAG_PATTERN.sub("", title)
    return re.sub(r"\s+", " ", without_tags).lower().strip()
