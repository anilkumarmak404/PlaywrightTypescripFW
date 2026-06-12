from __future__ import annotations

import json
import os
import urllib.error
import urllib.request
from typing import Any


def slack_configured() -> bool:
    return bool(os.environ.get("SLACK_WEBHOOK_URL"))


def send_slack_message(
    title: str,
    text: str,
    attachment_text: str | None = None,
    attachment_color: str | None = None,
) -> dict[str, Any]:
    webhook_url = os.environ.get("SLACK_WEBHOOK_URL")
    if not webhook_url:
        return {"status": "skipped", "message": "SLACK_WEBHOOK_URL is not configured"}

    payload = {
        "text": title,
        "blocks": [
            {
                "type": "header",
                "text": {
                    "type": "plain_text",
                    "text": title[:150],
                },
            },
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": text[:3000],
                },
            },
        ],
    }
    if attachment_text:
        payload["attachments"] = [
            {
                "color": attachment_color or "#d32f2f",
                "blocks": [
                    {
                        "type": "section",
                        "text": {
                            "type": "mrkdwn",
                            "text": attachment_text[:3000],
                        },
                    }
                ],
            }
        ]

    request = urllib.request.Request(
        webhook_url,
        data=json.dumps(payload).encode("utf-8"),
        method="POST",
        headers={"Content-Type": "application/json"},
    )

    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            return {"status": "sent", "statusCode": response.status}
    except urllib.error.HTTPError as error:
        detail = error.read().decode("utf-8", errors="ignore")
        return {"status": "failed", "message": f"Slack webhook failed with {error.code}: {detail}"}
    except urllib.error.URLError as error:
        return {"status": "failed", "message": f"Slack webhook request failed: {error.reason}"}
    except OSError as error:
        return {"status": "failed", "message": f"Slack webhook request failed: {error}"}
