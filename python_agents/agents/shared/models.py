from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any


Status = str
Severity = str


@dataclass
class TestMetadata:
    test_id: str
    feature: str
    owner: str
    jira: str


@dataclass
class NormalizedTestResult:
    run_id: str
    test_id: str
    title: str
    file: str
    framework: str
    feature: str
    owner: str
    jira: str
    status: Status
    duration_ms: int = 0
    retry: int = 0
    error_message: str | None = None
    stack: str | None = None
    screenshot_path: str | None = None
    trace_path: str | None = None
    video_path: str | None = None
    run_at: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class Finding:
    type: str
    severity: Severity
    message: str
    payload: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class TestRegistryItem:
    id: str
    title: str
    file: str
    feature: str
    owner: str
    jira: str
    tags: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class TestDeclaration:
    title: str
    file: str
    line: int
    framework: str
    modifier: str | None = None
    metadata_text: str = ""
