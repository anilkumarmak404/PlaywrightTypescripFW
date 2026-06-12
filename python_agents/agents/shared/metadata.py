from __future__ import annotations

import hashlib
import re

from .models import TestMetadata


def stable_unknown_id(title: str, file_path: str = "") -> str:
    digest = hashlib.sha1(f"{file_path}:{title}".encode("utf-8")).hexdigest()[:8].upper()
    return f"UNKNOWN-{digest}"


def extract_metadata(text: str, file_path: str = "") -> TestMetadata:
    test_id = _find_tag(text, "id") or stable_unknown_id(text, file_path)
    feature = _find_tag(text, "feature") or "unknown"
    owner = _find_tag(text, "owner") or "unknown"
    jira = _find_tag(text, "jira") or "UNKNOWN"

    return TestMetadata(test_id=test_id, feature=feature, owner=owner, jira=jira)


def missing_metadata(text: str, required: list[str]) -> list[str]:
    return [item for item in required if not _find_tag(text, item)]


def _find_tag(text: str, tag: str) -> str | None:
    match = re.search(rf"@{re.escape(tag)}:([a-zA-Z0-9-_]+)", text)
    return match.group(1) if match else None

