from __future__ import annotations

import os
from typing import Any

from .http_client import BasicAuthJsonClient


def confluence_configured(require_page: bool = False) -> bool:
    required = ["CONFLUENCE_BASE_URL", "CONFLUENCE_EMAIL", "CONFLUENCE_API_TOKEN"]
    if require_page:
        required.append("CONFLUENCE_PAGE_ID")
    return all(os.environ.get(key) for key in required)


class ConfluenceClient:
    def __init__(self) -> None:
        if not confluence_configured():
            raise RuntimeError("Missing Confluence environment variables")
        self.client = BasicAuthJsonClient(
            os.environ["CONFLUENCE_BASE_URL"].rstrip("/"),
            os.environ["CONFLUENCE_EMAIL"],
            os.environ["CONFLUENCE_API_TOKEN"],
        )

    def get_page(self, page_id: str) -> dict[str, Any]:
        return self.client.request("GET", f"/wiki/api/v2/pages/{page_id}", params={"body-format": "storage"})

    def update_page(self, page_id: str, title: str, version: int, status: str | None, html: str) -> dict[str, Any]:
        next_version = 1 if status == "draft" else version + 1
        return self.client.request("PUT", f"/wiki/api/v2/pages/{page_id}", {
            "id": page_id,
            "status": "current",
            "title": title,
            "body": {
                "representation": "storage",
                "value": html,
            },
            "version": {
                "number": next_version,
            },
        })


def get_confluence_page(page_id: str) -> dict[str, Any]:
    return ConfluenceClient().get_page(page_id)


def update_confluence_page(page_id: str, title: str, version: int, status: str | None, html: str) -> dict[str, Any]:
    return ConfluenceClient().update_page(page_id, title, version, status, html)
