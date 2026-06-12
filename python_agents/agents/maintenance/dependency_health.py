from __future__ import annotations

import json
import os
import subprocess

from ..shared.models import Finding


def check_dependency_health() -> list[Finding]:
    output = _npm_outdated_output()
    if not output:
        return []

    try:
        outdated = json.loads(output)
    except json.JSONDecodeError as error:
        return [
            Finding(
                type="dependency_update",
                severity="low",
                message="Unable to parse npm outdated output",
                payload={"error": str(error)},
            )
        ]

    findings: list[Finding] = []
    for package_name, info in outdated.items():
        current = info.get("current")
        latest = info.get("latest")
        if not current or not latest:
            continue

        is_playwright_related = "playwright" in package_name.lower()
        findings.append(
            Finding(
                type="dependency_update",
                severity="high" if is_playwright_related else "low",
                message=f"{package_name} is outdated. Current: {current}, latest: {latest}",
                payload={
                    "package": package_name,
                    "current": current,
                    "wanted": info.get("wanted"),
                    "latest": latest,
                },
            )
        )

    return findings


def _npm_outdated_output() -> str:
    try:
        completed = subprocess.run(
            [_npm_command(), "outdated", "--json"],
            capture_output=True,
            text=True,
            timeout=90,
            check=False,
        )
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return ""

    return completed.stdout.strip()


def _npm_command() -> str:
    return "npm.cmd" if os.name == "nt" else "npm"
