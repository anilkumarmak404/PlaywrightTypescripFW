from __future__ import annotations

from pathlib import Path
from typing import Any

from .io_utils import read_json as read_json_file
from .io_utils import write_json as write_json_file

STATE_DIR = Path("agent-state")


def state_path(file_name: str | Path) -> Path:
    target = Path(file_name)
    if target.is_absolute() or str(target).replace("\\", "/").startswith("agent-state/"):
        return target
    return STATE_DIR / target


def read_json(file_name: str | Path, fallback: Any) -> Any:
    return read_json_file(state_path(file_name), fallback)


def write_json(file_name: str | Path, data: Any) -> None:
    write_json_file(state_path(file_name), data)


def append_json_array(file_name: str | Path, item: Any) -> None:
    existing = read_json(file_name, [])
    if not isinstance(existing, list):
        existing = []
    existing.append(item)
    write_json(file_name, existing)
