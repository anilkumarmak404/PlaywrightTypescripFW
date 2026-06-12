from __future__ import annotations

import hashlib
import re

from .models import NormalizedTestResult


def create_failure_fingerprint(result: NormalizedTestResult) -> str:
    error = result.error_message or ""
    normalized_error = re.sub(r"\d+", "<num>", error)
    normalized_error = re.sub(r"\s+", " ", normalized_error)[:500]
    raw = "|".join([
        result.test_id,
        result.feature,
        normalized_error,
        result.file,
    ])
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()
