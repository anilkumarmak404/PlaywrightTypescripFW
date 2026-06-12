from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any


def load_env_file(path: str | Path) -> None:
    env_path = Path(path)
    if not env_path.exists():
        return

    for raw_line in env_path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue

        key, value = line.split("=", 1)
        os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))


def ensure_dir(path: str | Path) -> Path:
    target = Path(path)
    target.mkdir(parents=True, exist_ok=True)
    return target


def read_json(path: str | Path, fallback: Any) -> Any:
    target = Path(path)
    if not target.exists():
        return fallback

    return json.loads(target.read_text(encoding="utf-8"))


def write_json(path: str | Path, data: Any) -> None:
    target = Path(path)
    write_text(target, json.dumps(data, indent=2))


def write_text(path: str | Path, text: str) -> Path:
    target = Path(path)
    try:
        ensure_dir(target.parent)
        target.write_text(text, encoding="utf-8")
        return target
    except PermissionError:
        fallback = fallback_output_path(target)
        ensure_dir(fallback.parent)
        fallback.write_text(text, encoding="utf-8")
        print(f"Output path locked, wrote fallback file: {fallback}")
        return fallback


def fallback_output_path(original_path: Path) -> Path:
    safe_name = "__".join(original_path.parts).replace(":", "").replace("\\", "__").replace("/", "__")
    return Path("agent-state") / "python-agents" / safe_name


def simple_yaml_quality_gates(path: str | Path) -> dict[str, Any]:
    target = Path(path)
    if not target.exists():
        return {}

    result: dict[str, Any] = {}
    section: str | None = None

    for raw_line in target.read_text(encoding="utf-8").splitlines():
        if not raw_line.strip() or raw_line.strip().startswith("#"):
            continue

        if not raw_line.startswith(" ") and raw_line.endswith(":"):
            section = raw_line[:-1].strip()
            result[section] = {}
            continue

        if section and ":" in raw_line:
            key, value = raw_line.strip().split(":", 1)
            result[section][key.strip()] = _coerce_yaml_value(value.strip())
            continue

        if section and raw_line.strip().startswith("- "):
            result[section].setdefault("_list", []).append(raw_line.strip()[2:])

    maintenance = result.get("maintenance", {})
    if maintenance.get("_list") and "requireTestMetadata" not in maintenance:
        maintenance["requireTestMetadata"] = maintenance["_list"]

    return result


def _coerce_yaml_value(value: str) -> Any:
    if value.lower() in {"true", "false"}:
        return value.lower() == "true"
    try:
        if "." in value:
            return float(value)
        return int(value)
    except ValueError:
        return value
