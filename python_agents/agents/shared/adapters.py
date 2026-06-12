from __future__ import annotations

import glob
import hashlib
import json
import time
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Iterable

from .metadata import extract_metadata
from .models import NormalizedTestResult


def load_results(framework: str = "auto", result_paths: list[str] | None = None) -> list[NormalizedTestResult]:
    paths = _expand_paths(result_paths or _default_result_paths(framework))

    if framework == "auto":
        return _load_auto(paths)
    if framework in {"junit", "selenium", "pytest"}:
        return _load_junit(paths, framework)
    if framework in {"playwright", "playwright-agent"}:
        return _load_playwright_agent(paths) or _load_junit(paths, "playwright")
    if framework == "cypress":
        return _load_cypress(paths) or _load_junit(paths, "cypress")
    if framework == "generic":
        return _load_junit(paths, "generic")

    raise ValueError(f"Unsupported framework: {framework}")


def _default_result_paths(framework: str) -> list[str]:
    if framework in {"playwright", "playwright-agent"}:
        return [
            "reports/ai-summary/latest-agent-results.json",
            "test-results/results.json",
            "test-results/**/*.xml",
        ]
    if framework in {"selenium", "junit"}:
        return [
            "target/surefire-reports/*.xml",
            "target/failsafe-reports/*.xml",
            "build/test-results/test/*.xml",
            "**/junit*.xml",
        ]
    if framework == "cypress":
        return [
            "cypress/reports/**/*.json",
            "cypress/results/**/*.xml",
            "test-results/**/*.xml",
        ]
    return [
        "reports/ai-summary/latest-agent-results.json",
        "test-results/**/*.xml",
        "target/surefire-reports/*.xml",
        "build/test-results/**/*.xml",
        "cypress/reports/**/*.json",
        "**/junit*.xml",
    ]


def _expand_paths(patterns: Iterable[str]) -> list[Path]:
    paths: list[Path] = []
    for pattern in patterns:
        matches = glob.glob(pattern, recursive=True)
        paths.extend(Path(match) for match in matches if Path(match).is_file() and not _is_ignored_path(Path(match)))
    return sorted(set(paths))


def _is_ignored_path(path: Path) -> bool:
    normalized = str(path).replace("\\", "/")
    ignored_parts = [
        "/node_modules/",
        "node_modules/",
        "/allure-report/",
        "/playwright-report/",
        "/.git/",
    ]
    return any(part in normalized for part in ignored_parts)


def _load_auto(paths: list[Path]) -> list[NormalizedTestResult]:
    for loader in (_load_playwright_agent, _load_playwright_json, _load_cypress):
        loaded = loader(paths)
        if loaded:
            return loaded

    return _load_junit(paths, "generic")


def _load_playwright_agent(paths: list[Path]) -> list[NormalizedTestResult]:
    for path in paths:
        if path.name != "latest-agent-results.json":
            continue

        data = json.loads(path.read_text(encoding="utf-8"))
        results = data.get("results", [])
        run_id = data.get("runId") or _run_id("playwright-agent")

        return [_from_agent_json(item, run_id, "playwright") for item in results]

    return []


def _from_agent_json(item: dict, run_id: str, framework: str) -> NormalizedTestResult:
    title = str(item.get("title") or item.get("testId") or "unknown")
    metadata = extract_metadata(title, str(item.get("file") or ""))
    status = _normalize_status(str(item.get("status") or "unknown"))

    return NormalizedTestResult(
        run_id=str(item.get("runId") or run_id),
        test_id=str(item.get("testId") or metadata.test_id),
        title=title,
        file=str(item.get("file") or ""),
        framework=framework,
        feature=str(item.get("feature") or metadata.feature),
        owner=str(item.get("owner") or metadata.owner),
        jira=str(item.get("jira") or metadata.jira),
        status=status,
        duration_ms=int(item.get("durationMs") or 0),
        retry=int(item.get("retry") or 0),
        error_message=item.get("errorMessage"),
        stack=item.get("stack"),
        screenshot_path=item.get("screenshotPath"),
        trace_path=item.get("tracePath"),
        video_path=item.get("videoPath"),
        run_at=item.get("runAt"),
    )


def _load_playwright_json(paths: list[Path]) -> list[NormalizedTestResult]:
    for path in paths:
        if path.name != "results.json":
            continue

        data = json.loads(path.read_text(encoding="utf-8"))
        run_id = _run_id("playwright-json")
        results: list[NormalizedTestResult] = []
        _walk_playwright_suite(data, results, run_id)
        if results:
            return results

    return []


def _walk_playwright_suite(node: dict, results: list[NormalizedTestResult], run_id: str) -> None:
    for suite in node.get("suites", []):
        _walk_playwright_suite(suite, results, run_id)

    for spec in node.get("specs", []):
        title = str(spec.get("title") or "unknown")
        file_path = str(spec.get("file") or node.get("file") or "")
        metadata = extract_metadata(title, file_path)

        for test in spec.get("tests", []):
            test_results = test.get("results", [])
            last_result = test_results[-1] if test_results else {}
            status = _normalize_status(str(last_result.get("status") or test.get("outcome") or "unknown"))
            error = last_result.get("error") or {}

            results.append(NormalizedTestResult(
                run_id=run_id,
                test_id=metadata.test_id,
                title=title,
                file=file_path,
                framework="playwright",
                feature=metadata.feature,
                owner=metadata.owner,
                jira=metadata.jira,
                status=status,
                duration_ms=int(last_result.get("duration") or 0),
                retry=max(len(test_results) - 1, 0),
                error_message=error.get("message"),
                stack=error.get("stack"),
            ))


def _load_junit(paths: list[Path], framework: str) -> list[NormalizedTestResult]:
    xml_paths = [path for path in paths if path.suffix.lower() == ".xml"]
    results: list[NormalizedTestResult] = []
    run_id = _run_id(framework)

    for path in xml_paths:
        try:
            root = ET.parse(path).getroot()
        except ET.ParseError:
            continue

        for testcase in root.iter("testcase"):
            name = testcase.attrib.get("name", "unknown")
            classname = testcase.attrib.get("classname", "")
            title = f"{classname} {name}".strip()
            metadata = extract_metadata(title, str(path))
            failure = testcase.find("failure")
            error = testcase.find("error")
            skipped = testcase.find("skipped")
            status = "passed"
            message = None
            stack = None

            if skipped is not None:
                status = "skipped"
                message = skipped.attrib.get("message")
            elif failure is not None:
                status = "failed"
                message = failure.attrib.get("message") or (failure.text or "").strip()
                stack = failure.text
            elif error is not None:
                status = "failed"
                message = error.attrib.get("message") or (error.text or "").strip()
                stack = error.text

            results.append(NormalizedTestResult(
                run_id=run_id,
                test_id=metadata.test_id,
                title=title,
                file=str(path),
                framework=framework,
                feature=metadata.feature,
                owner=metadata.owner,
                jira=metadata.jira,
                status=status,
                duration_ms=int(float(testcase.attrib.get("time", "0")) * 1000),
                error_message=message,
                stack=stack,
            ))

    return results


def _load_cypress(paths: list[Path]) -> list[NormalizedTestResult]:
    results: list[NormalizedTestResult] = []
    run_id = _run_id("cypress")

    for path in paths:
        if path.suffix.lower() != ".json":
            continue

        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            continue

        _walk_cypress_node(data, results, run_id, str(path))

    return results


def _walk_cypress_node(node, results: list[NormalizedTestResult], run_id: str, file_path: str) -> None:
    if isinstance(node, dict):
        tests = node.get("tests", [])
        for test in tests:
            title_parts = test.get("fullTitle") or test.get("title") or "unknown"
            title = " ".join(title_parts) if isinstance(title_parts, list) else str(title_parts)
            metadata = extract_metadata(title, file_path)
            state = str(test.get("state") or test.get("status") or "unknown")
            err = test.get("err") or {}

            results.append(NormalizedTestResult(
                run_id=run_id,
                test_id=metadata.test_id,
                title=title,
                file=str(test.get("file") or file_path),
                framework="cypress",
                feature=metadata.feature,
                owner=metadata.owner,
                jira=metadata.jira,
                status=_normalize_status(state),
                duration_ms=int(test.get("duration") or 0),
                error_message=err.get("message") if isinstance(err, dict) else None,
                stack=err.get("stack") if isinstance(err, dict) else None,
            ))

        for key in ("results", "suites"):
            child = node.get(key)
            if child:
                _walk_cypress_node(child, results, run_id, file_path)
    elif isinstance(node, list):
        for item in node:
            _walk_cypress_node(item, results, run_id, file_path)


def _normalize_status(status: str) -> str:
    value = status.lower()
    if value in {"passed", "pass", "ok"}:
        return "passed"
    if value in {"failed", "fail", "failure", "error", "timedout", "timed_out", "timed out"}:
        return "failed"
    if value in {"skipped", "skip", "pending", "disabled"}:
        return "skipped"
    if value == "flaky":
        return "flaky"
    return "unknown"


def _run_id(prefix: str) -> str:
    raw = f"{prefix}-{time.time_ns()}"
    return hashlib.sha1(raw.encode("utf-8")).hexdigest()[:16]
