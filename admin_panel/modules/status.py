#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from __future__ import annotations

import json
import socket
import time

from admin_panel.modules.characters import clear_online_flags, online_count
from admin_panel.modules.config import CONFIG, PROXY_CONFIG_PATH, RUNNING_IN_DOCKER
from admin_panel.modules.db import fetch_one
from admin_panel.modules.realms import active_realm_name

STATUS_CACHE: dict | None = None
STATUS_CACHE_TIME = 0.0
STATUS_CACHE_TTL = 10.0
STATUS_SOCKET_TIMEOUT = 0.08


def host_candidates(host: str, service_name: str) -> list[str]:
    if host in ("", "0.0.0.0", "::"):
        if RUNNING_IN_DOCKER:
            return [service_name, "127.0.0.1", "localhost"]
        return ["127.0.0.1", "localhost"]
    return [host]


def load_proxy_config() -> dict:
    try:
        return json.loads(PROXY_CONFIG_PATH.read_text(encoding="utf-8"))
    except Exception:
        return {}


def proxy_listen_ports() -> list[int]:
    cfg = load_proxy_config()
    ports: list[int] = []
    states = cfg.get("states") or {}
    state = states.get("default") or next(iter(states.values()), {})
    for route in (state.get("routes") or {}).values():
        try:
            ports.append(int(route.get("listen")))
        except (TypeError, ValueError):
            continue
    telnet = ((cfg.get("shared") or {}).get("telnet") or {})
    try:
        ports.append(int(telnet.get("port")))
    except (TypeError, ValueError):
        pass
    return sorted(set(port for port in ports if port > 0))


def port_open(hosts: list[str], port: int, timeout: float = STATUS_SOCKET_TIMEOUT) -> bool:
    for host in hosts:
        try:
            with socket.create_connection((host, port), timeout=timeout):
                return True
        except OSError:
            continue
    return False


def current_online_count() -> int:
    try:
        return online_count()
    except Exception:
        return 0


def reset_stale_online_flags() -> None:
    try:
        clear_online_flags()
    except Exception:
        pass


def server_status(*, force: bool = False) -> dict:
    global STATUS_CACHE, STATUS_CACHE_TIME
    now = time.monotonic()
    if not force and STATUS_CACHE is not None and now - STATUS_CACHE_TIME < STATUS_CACHE_TTL:
        status = dict(STATUS_CACHE)
        if status.get("database") and not status.get("worldserver"):
            reset_stale_online_flags()
            status["online_count"] = 0
        else:
            status["online_count"] = current_online_count()
        return status

    status = {
        "database": False,
        "authserver": False,
        "worldserver": False,
        "proxyserver": False,
        "realm": "",
        "online_count": 0,
    }

    try:
        status["database"] = bool(fetch_one("auth", "SELECT 1 AS ok"))
    except Exception:
        status["database"] = False

    auth_cfg = CONFIG.get("authserver", {})
    world_cfg = CONFIG.get("worldserver", {})
    status["authserver"] = port_open(
        host_candidates(str(auth_cfg.get("host", "127.0.0.1")), "authserver"),
        int(auth_cfg.get("port", 3720)),
    )
    status["worldserver"] = port_open(
        host_candidates(str(world_cfg.get("host", "127.0.0.1")), "worldserver"),
        int(world_cfg.get("port", 8086)),
    )
    status["proxyserver"] = any(
        port_open(host_candidates("0.0.0.0", "proxyserver"), port)
        for port in proxy_listen_ports()
    )
    if status["database"] and not status["worldserver"]:
        reset_stale_online_flags()
        status["online_count"] = 0
    elif status["database"]:
        status["online_count"] = current_online_count()

    if status["worldserver"]:
        status["realm"] = active_realm_name()

    STATUS_CACHE = dict(status)
    STATUS_CACHE_TIME = now
    return status
