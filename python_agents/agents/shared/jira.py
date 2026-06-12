from __future__ import annotations

import os
from typing import Any

from .http_client import BasicAuthJsonClient, HttpError


def jira_env_summary() -> dict[str, Any]:
    return {
        "baseUrl": os.environ.get("JIRA_BASE_URL", ""),
        "email": os.environ.get("JIRA_EMAIL", ""),
        "tokenConfigured": bool(os.environ.get("JIRA_API_TOKEN")),
        "tokenLength": len(os.environ.get("JIRA_API_TOKEN", "")),
        "projectKey": os.environ.get("JIRA_PROJECT_KEY", ""),
        "projectId": os.environ.get("JIRA_PROJECT_ID", ""),
        "issueType": os.environ.get("JIRA_ISSUE_TYPE", ""),
    }


def jira_configured(require_project: bool = False) -> bool:
    required = ["JIRA_BASE_URL", "JIRA_EMAIL", "JIRA_API_TOKEN"]
    has_base = all(os.environ.get(key) for key in required)
    if require_project:
        return has_base and bool(os.environ.get("JIRA_PROJECT_KEY") or os.environ.get("JIRA_PROJECT_ID"))
    return has_base


class JiraClient:
    def __init__(self) -> None:
        if not jira_configured():
            raise RuntimeError("Missing Jira environment variables")

        self.base_url = os.environ["JIRA_BASE_URL"].rstrip("/")
        self.client = BasicAuthJsonClient(
            self.base_url,
            os.environ["JIRA_EMAIL"],
            os.environ["JIRA_API_TOKEN"],
        )

    def verify_auth(self) -> dict[str, Any]:
        return self.client.request("GET", "/rest/api/3/myself")

    def validate_access(self) -> None:
        project_id = os.environ.get("JIRA_PROJECT_ID")
        project_key = os.environ.get("JIRA_PROJECT_KEY")
        project_id_or_key = project_id or project_key
        if not project_id_or_key:
            raise RuntimeError("Missing JIRA_PROJECT_KEY or JIRA_PROJECT_ID")

        self.verify_auth()
        self.client.request("GET", f"/rest/api/3/project/{project_id_or_key}")
        permissions = self.client.request("GET", "/rest/api/3/mypermissions", params={
            "projectKey": project_key if project_key and not project_id else None,
            "projectId": project_id,
            "permissions": "BROWSE_PROJECTS,CREATE_ISSUES",
        })
        permission_map = permissions.get("permissions", {})
        can_browse = permission_map.get("BROWSE_PROJECTS", {}).get("havePermission")
        can_create = permission_map.get("CREATE_ISSUES", {}).get("havePermission")
        if not can_browse or not can_create:
            raise RuntimeError(
                f"Jira user lacks project permissions. BROWSE_PROJECTS={bool(can_browse)}, "
                f"CREATE_ISSUES={bool(can_create)}"
            )

    def get_issue(self, issue_key: str) -> dict[str, Any]:
        return self.client.request(
            "GET",
            f"/rest/api/3/issue/{issue_key}",
            params={"fields": "summary,description,updated,status,labels"},
        )

    def add_comment(self, issue_key: str, text: str) -> None:
        self.client.request("POST", f"/rest/api/3/issue/{issue_key}/comment", {
            "body": to_jira_adf(text),
        })

    def search_by_fingerprint(self, fingerprint: str) -> dict[str, Any] | None:
        data = self.client.request("POST", "/rest/api/3/search/jql", {
            "jql": f'labels = "fp-{fingerprint[:12]}" AND statusCategory != Done',
            "maxResults": 1,
            "fields": ["key", "summary", "status"],
        })
        issues = data.get("issues") or []
        return issues[0] if issues else None

    def create_bug(self, summary: str, description: str, fingerprint: str, labels: list[str]) -> dict[str, Any]:
        project_key = os.environ.get("JIRA_PROJECT_KEY")
        project_id = os.environ.get("JIRA_PROJECT_ID")
        if not project_key and not project_id:
            raise RuntimeError("Missing JIRA_PROJECT_KEY or JIRA_PROJECT_ID")

        issue_types = [os.environ["JIRA_ISSUE_TYPE"]] if os.environ.get("JIRA_ISSUE_TYPE") else ["Task", "Bug"]
        errors: list[str] = []

        for issue_type in issue_types:
            payload = {
                "fields": {
                    "project": {"id": project_id} if project_id else {"key": project_key},
                    "issuetype": {"name": issue_type},
                    "summary": summary,
                    "description": to_jira_adf(description),
                    "labels": [_sanitize_label(label) for label in ["playwright-auto", f"fp-{fingerprint[:12]}", *labels]],
                }
            }
            try:
                return self.client.request("POST", "/rest/api/3/issue", payload)
            except HttpError as error:
                errors.append(f"{issue_type}: {error}")

        raise RuntimeError("Unable to create Jira issue. " + " | ".join(errors))

    def update_summary(self, issue_key: str, summary: str) -> None:
        self.client.request("PUT", f"/rest/api/3/issue/{issue_key}", {"fields": {"summary": summary}})

    def attach_file(self, issue_key: str, file_path: str | None) -> None:
        if not file_path:
            return
        self.client.upload_file(
            f"/rest/api/3/issue/{issue_key}/attachments",
            file_path,
            {"X-Atlassian-Token": "no-check"},
        )


def verify_jira_auth() -> dict[str, Any]:
    return JiraClient().verify_auth()


def validate_jira_access() -> None:
    JiraClient().validate_access()


def search_jira_issue_by_fingerprint(fingerprint: str) -> dict[str, Any] | None:
    return JiraClient().search_by_fingerprint(fingerprint)


def create_jira_bug(summary: str, description: str, fingerprint: str, labels: list[str] | None = None) -> dict[str, Any]:
    return JiraClient().create_bug(summary, description, fingerprint, labels or [])


def update_jira_issue_summary(issue_key: str, summary: str) -> None:
    JiraClient().update_summary(issue_key, summary)


def add_jira_comment(issue_key: str, text: str) -> None:
    JiraClient().add_comment(issue_key, text)


def get_jira_issue(issue_key: str) -> dict[str, Any]:
    return JiraClient().get_issue(issue_key)


def add_jira_issue_comment(issue_key: str, text: str) -> None:
    add_jira_comment(issue_key, text)


def attach_file_to_jira(issue_key: str, file_path: str | None) -> None:
    JiraClient().attach_file(issue_key, file_path)


def to_jira_adf(text: str) -> dict[str, Any]:
    content = []
    for line in text.splitlines():
        is_bold = line.startswith("**") and line.endswith("**") and len(line) > 4
        clean_text = line[2:-2] if is_bold else line
        content.append({
            "type": "paragraph",
            "content": [
                {
                    "type": "text",
                    "text": clean_text,
                    **({"marks": [{"type": "strong"}]} if is_bold else {}),
                }
            ] if clean_text else [],
        })
    return {"type": "doc", "version": 1, "content": content}


def _sanitize_label(label: str) -> str:
    return "".join(char if char.isalnum() or char in "_-" else "-" for char in label)[:255]
