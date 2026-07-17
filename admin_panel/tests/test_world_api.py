#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from __future__ import annotations

import json

import pytest

from admin_panel.modules import world_api


class _Response:
    def __init__(self, payload: dict):
        self.payload = payload

    def __enter__(self):
        return self

    def __exit__(self, *_args):
        return False

    def read(self) -> bytes:
        return json.dumps(self.payload).encode("utf-8")


def test_world_chat_uses_chat_api(monkeypatch):
    captured = {}

    def fake_urlopen(request, timeout):
        captured["url"] = request.full_url
        captured["headers"] = dict(request.headers)
        captured["payload"] = json.loads(request.data.decode("utf-8"))
        captured["timeout"] = timeout
        return _Response({"ok": True})

    monkeypatch.setattr(world_api, "_api_config", lambda: ("http://api.test:8090", "secret"))
    monkeypatch.setattr(world_api, "urlopen", fake_urlopen)

    world_api.send_world_chat("Server restart soon", "ADMIN")

    assert captured["url"] == "http://api.test:8090/api/chat/world"
    assert captured["headers"]["Authorization"] == "Bearer secret"
    assert captured["payload"] == {
        "message": "Server restart soon",
        "author": "ADMIN",
        "source": "Admin Panel",
    }
    assert captured["timeout"] == 5.0


def test_whisper_uses_target_player(monkeypatch):
    captured = {}

    def fake_urlopen(request, timeout):
        captured["url"] = request.full_url
        captured["payload"] = json.loads(request.data.decode("utf-8"))
        return _Response({"ok": True})

    monkeypatch.setattr(world_api, "_api_config", lambda: ("http://api.test:8090", ""))
    monkeypatch.setattr(world_api, "urlopen", fake_urlopen)

    world_api.send_whisper("Thrall", "Lok'tar", "ADMIN")

    assert captured["url"].endswith("/api/chat/whisper")
    assert captured["payload"]["target_name"] == "Thrall"
    assert captured["payload"]["source"] == "Admin Panel"


def test_system_mail_uses_mail_api(monkeypatch):
    captured = {}

    def fake_urlopen(request, timeout):
        captured["url"] = request.full_url
        captured["payload"] = json.loads(request.data.decode("utf-8"))
        return _Response({"ok": True, "mail_id": 42})

    monkeypatch.setattr(world_api, "_api_config", lambda: ("http://api.test:8090", ""))
    monkeypatch.setattr(world_api, "urlopen", fake_urlopen)

    result = world_api.send_system_mail("Jaina", "Welcome", "Welcome to Pandaria.")

    assert captured["url"].endswith("/api/mail/system")
    assert captured["payload"] == {
        "recipient": "Jaina",
        "subject": "Welcome",
        "body": "Welcome to Pandaria.",
    }
    assert result["mail_id"] == 42


def test_unavailable_api_has_safe_admin_error(monkeypatch):
    def unavailable(_request, timeout):
        raise TimeoutError

    monkeypatch.setattr(world_api, "_api_config", lambda: ("http://api.test:8090", ""))
    monkeypatch.setattr(world_api, "urlopen", unavailable)

    with pytest.raises(world_api.WorldAPIError, match="Worldserver API is unavailable"):
        world_api.send_world_chat("Hello", "ADMIN")
