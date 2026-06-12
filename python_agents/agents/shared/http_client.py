from __future__ import annotations

import base64
import json
import mimetypes
import os
import urllib.error
import urllib.parse
import urllib.request
import uuid
from pathlib import Path
from typing import Any


class HttpError(RuntimeError):
    pass


class BasicAuthJsonClient:
    def __init__(self, base_url: str, email: str, token: str) -> None:
        self.base_url = base_url.rstrip("/")
        auth = base64.b64encode(f"{email}:{token}".encode("utf-8")).decode("ascii")
        self.base_headers = {
            "Authorization": f"Basic {auth}",
            "Accept": "application/json",
        }

    def request(
        self,
        method: str,
        path: str,
        data: dict[str, Any] | None = None,
        params: dict[str, Any] | None = None,
        headers: dict[str, str] | None = None,
    ) -> Any:
        url = f"{self.base_url}{path}"
        if params:
            clean = {key: value for key, value in params.items() if value is not None}
            url = f"{url}?{urllib.parse.urlencode(clean)}"

        body = None
        request_headers = {**self.base_headers, **(headers or {})}
        if data is not None:
            body = json.dumps(data).encode("utf-8")
            request_headers["Content-Type"] = "application/json"

        request = urllib.request.Request(url, data=body, method=method, headers=request_headers)
        try:
            with urllib.request.urlopen(request, timeout=30) as response:
                text = response.read().decode("utf-8")
                return json.loads(text) if text else {}
        except urllib.error.HTTPError as error:
            detail = error.read().decode("utf-8", errors="ignore")
            raise HttpError(f"{method} {path} failed with {error.code}: {detail}") from error
        except urllib.error.URLError as error:
            raise HttpError(f"{method} {path} failed: {error.reason}") from error

    def upload_file(self, path: str, file_path: str, extra_headers: dict[str, str] | None = None) -> Any:
        target = Path(file_path)
        if not target.exists():
            return {}

        boundary = f"----python-agent-{uuid.uuid4().hex}"
        file_name = target.name
        content_type = mimetypes.guess_type(file_name)[0] or "application/octet-stream"
        file_bytes = target.read_bytes()
        body = (
            f"--{boundary}\r\n"
            f'Content-Disposition: form-data; name="file"; filename="{file_name}"\r\n'
            f"Content-Type: {content_type}\r\n\r\n"
        ).encode("utf-8") + file_bytes + f"\r\n--{boundary}--\r\n".encode("utf-8")

        headers = {
            **self.base_headers,
            **(extra_headers or {}),
            "Content-Type": f"multipart/form-data; boundary={boundary}",
        }
        request = urllib.request.Request(
            f"{self.base_url}{path}",
            data=body,
            method="POST",
            headers=headers,
        )

        try:
            with urllib.request.urlopen(request, timeout=60) as response:
                text = response.read().decode("utf-8")
                return json.loads(text) if text else {}
        except urllib.error.HTTPError as error:
            detail = error.read().decode("utf-8", errors="ignore")
            raise HttpError(f"POST {path} failed with {error.code}: {detail}") from error


def env_summary(prefix: str, keys: list[str]) -> dict[str, Any]:
    return {
        key: {
            "configured": bool(os.environ.get(f"{prefix}_{key}")),
            "length": len(os.environ.get(f"{prefix}_{key}") or ""),
        }
        for key in keys
    }

