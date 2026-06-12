from __future__ import annotations

import glob
import re
from pathlib import Path

from ..shared.models import TestRegistryItem


TEST_PATTERN = re.compile(r"test(?:\.(?:only|skip|fixme|fail|slow))?\(\s*['\"`]([^'\"`]+)['\"`]")
ID_PATTERN = re.compile(r"@id:([A-Z0-9-_]+)")
FEATURE_PATTERN = re.compile(r"@feature:([a-zA-Z0-9-_]+)")
OWNER_PATTERN = re.compile(r"@owner:([a-zA-Z0-9-_]+)")
JIRA_PATTERN = re.compile(r"@jira:([A-Z0-9-]+)")
TAG_PATTERN = re.compile(r"@[a-zA-Z0-9-_:]+")


def scan_tests(pattern: str = "tests/**/*.spec.ts") -> list[TestRegistryItem]:
    registry: list[TestRegistryItem] = []
    files = sorted(Path(match) for match in glob.glob(pattern, recursive=True))

    for file_path in files:
        if not file_path.is_file():
            continue
        text = file_path.read_text(encoding="utf-8", errors="ignore")
        registry.extend(extract_meta_from_text(text, _normalize_path(file_path)))

    return registry


def extract_meta_from_text(text: str, file_path: str) -> list[TestRegistryItem]:
    items: list[TestRegistryItem] = []

    for match in TEST_PATTERN.finditer(text):
        title = match.group(1)
        test_id = _first(ID_PATTERN, title)
        if not test_id:
            continue

        items.append(TestRegistryItem(
            id=test_id,
            title=title,
            file=file_path,
            feature=_first(FEATURE_PATTERN, title) or "unknown",
            owner=_first(OWNER_PATTERN, title) or "unknown",
            jira=_first(JIRA_PATTERN, title) or "UNKNOWN",
            tags=TAG_PATTERN.findall(title),
        ))

    return items


def _first(pattern: re.Pattern[str], text: str) -> str | None:
    match = pattern.search(text)
    return match.group(1) if match else None


def _normalize_path(path: Path) -> str:
    return str(path).replace("\\", "/")
