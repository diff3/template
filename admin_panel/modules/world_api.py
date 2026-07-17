#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from __future__ import annotations

import json
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from admin_panel.modules.config import CONFIG, RUNNING_IN_DOCKER


class WorldAPIError(RuntimeError):
    pass


def _api_config() -> tuple[str, str]:
    section = dict(CONFIG.get("Api") or {})
    host = str(section.get("Host", "127.0.0.1") or "127.0.0.1").strip()
    if host in {"0.0.0.0", "::", "[::]"}:
        host = "worldserver" if RUNNING_IN_DOCKER else "127.0.0.1"
    port = int(section.get("Port", 8090) or 8090)
    token = str(section.get("Token", "") or "")
    return f"http://{host}:{port}", token


def post(path: str, payload: dict) -> dict:
    base_url, token = _api_config()
    body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    headers = {"Content-Type": "application/json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    request = Request(f"{base_url}{path}", data=body, headers=headers, method="POST")

    try:
        with urlopen(request, timeout=5.0) as response:
            raw = response.read()
    except HTTPError as exc:
        try:
            detail = json.loads(exc.read().decode("utf-8")).get("error")
        except (UnicodeDecodeError, json.JSONDecodeError, AttributeError):
            detail = None
        raise WorldAPIError(str(detail or f"API request failed ({exc.code}).")) from exc
    except (URLError, TimeoutError, OSError) as exc:
        raise WorldAPIError("Worldserver API is unavailable.") from exc

    try:
        result = json.loads(raw.decode("utf-8")) if raw else {}
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise WorldAPIError("Worldserver API returned an invalid response.") from exc
    if not isinstance(result, dict):
        raise WorldAPIError("Worldserver API returned an invalid response.")
    return result


def send_world_chat(message: str, author: str) -> dict:
    return post("/api/chat/world", {
        "message": message,
        "author": author,
        "source": "Admin Panel",
    })


def send_whisper(target_name: str, message: str, author: str) -> dict:
    return post("/api/chat/whisper", {
        "target_name": target_name,
        "message": message,
        "author": author,
        "source": "Admin Panel",
    })


def send_system_mail(recipient: str, subject: str, body: str) -> dict:
    return post("/api/mail/system", {
        "recipient": recipient,
        "subject": subject,
        "body": body,
    })
