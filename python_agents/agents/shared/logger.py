from __future__ import annotations

from datetime import datetime, timezone


def info(message: str) -> None:
    print(_format("INFO", message))


def warn(message: str) -> None:
    print(_format("WARN", message))


def error(message: str) -> None:
    print(_format("ERROR", message))


def _format(level: str, message: str) -> str:
    timestamp = datetime.now(timezone.utc).isoformat()
    return f"[{timestamp}] [{level}] {message}"
