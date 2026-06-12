from __future__ import annotations

import glob
import re
from pathlib import Path

from .models import TestDeclaration


DEFAULT_TEST_PATTERNS = [
    "tests/**/*.ts",
    "tests/**/*.js",
    "tests/**/*.java",
    "src/test/**/*.java",
    "cypress/e2e/**/*.js",
    "cypress/e2e/**/*.ts",
    "e2e/**/*.ts",
    "e2e/**/*.js",
    "tests/**/*.py",
]


JS_TEST_PATTERN = re.compile(r"\b(test|it|describe)\s*(?:\.\s*(only|skip|fixme))?\s*\(\s*['\"]([^'\"]+)['\"]")
JAVA_TEST_PATTERN = re.compile(r"@(Test|Disabled|Ignore)\b")
PY_TEST_PATTERN = re.compile(r"^\s*def\s+(test_[a-zA-Z0-9_]+)\s*\(")


def scan_test_declarations(patterns: list[str] | None = None) -> list[TestDeclaration]:
    declarations: list[TestDeclaration] = []
    files = _expand(patterns or DEFAULT_TEST_PATTERNS)

    for file_path in files:
        lines = file_path.read_text(encoding="utf-8", errors="ignore").splitlines()
        framework = _framework_from_path(file_path)

        for index, line in enumerate(lines):
            context = "\n".join(lines[max(0, index - 2): index + 1])

            for match in JS_TEST_PATTERN.finditer(line):
                kind = match.group(1)
                modifier = match.group(2)
                if kind == "describe" and modifier != "only":
                    continue

                declarations.append(TestDeclaration(
                    title=match.group(3),
                    file=str(file_path),
                    line=index + 1,
                    framework=framework,
                    modifier=modifier,
                    metadata_text=f"{context}\n{match.group(3)}",
                ))

            if JAVA_TEST_PATTERN.search(line):
                declarations.append(TestDeclaration(
                    title=_java_title(lines, index),
                    file=str(file_path),
                    line=index + 1,
                    framework="selenium-java",
                    modifier=_java_modifier(line),
                    metadata_text=context,
                ))

            py_match = PY_TEST_PATTERN.search(line)
            if py_match:
                declarations.append(TestDeclaration(
                    title=py_match.group(1),
                    file=str(file_path),
                    line=index + 1,
                    framework="pytest",
                    metadata_text=f"{context}\n{py_match.group(1)}",
                ))

    return declarations


def _expand(patterns: list[str]) -> list[Path]:
    files: list[Path] = []
    for pattern in patterns:
        files.extend(Path(match) for match in glob.glob(pattern, recursive=True))
    return sorted(path for path in set(files) if path.is_file() and "-snapshots" not in str(path))


def _framework_from_path(path: Path) -> str:
    text = str(path).replace("\\", "/").lower()
    if "cypress/" in text:
        return "cypress"
    if text.endswith(".java"):
        return "selenium-java"
    if text.endswith(".py"):
        return "pytest"
    return "playwright-or-js"


def _java_title(lines: list[str], index: int) -> str:
    for line in lines[index:index + 5]:
        method = re.search(r"\bvoid\s+([a-zA-Z0-9_]+)\s*\(", line)
        if method:
            return method.group(1)
    return lines[index].strip()


def _java_modifier(line: str) -> str | None:
    if "@Disabled" in line or "@Ignore" in line:
        return "skip"
    return None
