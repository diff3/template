#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from __future__ import annotations

import yaml

from admin_panel.modules.config import CONFIG, DEFAULT_CONFIG_PATH
from admin_panel.modules.db import db_cursor, fetch_all, fetch_one


def realm_rows() -> list[dict]:
    return fetch_all(
        "auth",
        """
        SELECT id, name, address, port, icon, flag, timezone, allowedSecurityLevel
        FROM realmlist
        ORDER BY id ASC
        """,
    )


def realm_count() -> int:
    row = fetch_one("auth", "SELECT COUNT(*) AS count FROM realmlist")
    return int((row or {}).get("count") or 0)


def next_realm_id() -> int:
    row = fetch_one("auth", "SELECT COALESCE(MAX(id), 0) + 1 AS next_id FROM realmlist")
    return int((row or {}).get("next_id") or 1)


def realm_defaults() -> dict:
    first_realm = fetch_one(
        "auth",
        """
        SELECT address, port, flag, timezone, allowedSecurityLevel
        FROM realmlist
        ORDER BY id ASC
        LIMIT 1
        """,
    ) or {}
    return {
        "address": first_realm.get("address") or "127.0.0.1",
        "port": int(first_realm.get("port") or CONFIG.get("worldserver", {}).get("port", 8086)),
        "flag": int(first_realm.get("flag") or 0),
        "timezone": int(first_realm.get("timezone") or 1),
        "allowedSecurityLevel": int(first_realm.get("allowedSecurityLevel") or 0),
    }


def get_realm(realm_id: int) -> dict | None:
    return fetch_one("auth", "SELECT * FROM realmlist WHERE id = %s", (realm_id,))


def active_realm_name() -> str:
    world_port = int(CONFIG.get("worldserver", {}).get("port", 8086))
    try:
        realm = fetch_one(
            "auth",
            """
            SELECT name
            FROM realmlist
            WHERE port = %s
            ORDER BY id ASC
            LIMIT 1
            """,
            (world_port,),
        )
        if not realm:
            realm = fetch_one("auth", "SELECT name FROM realmlist ORDER BY id ASC LIMIT 1")
    except Exception:
        realm = None
    return str((realm or {}).get("name") or "")


def insert_realm(name: str, icon: int) -> None:
    defaults = realm_defaults()
    with db_cursor("auth") as (_conn, cursor):
        cursor.execute(
            """
            INSERT INTO realmlist
                (id, name, address, port, icon, flag, timezone, allowedSecurityLevel)
            VALUES
                (%s, %s, %s, %s, %s, %s, %s, %s)
            """,
            (
                next_realm_id(),
                name,
                defaults["address"],
                defaults["port"],
                icon,
                defaults["flag"],
                defaults["timezone"],
                defaults["allowedSecurityLevel"],
            ),
        )


def update_realm(realm_id: int, name: str, icon: int) -> None:
    with db_cursor("auth") as (_conn, cursor):
        cursor.execute(
            """
            UPDATE realmlist
            SET name = %s, icon = %s
            WHERE id = %s
            """,
            (name, icon, realm_id),
        )


def delete_realm(realm_id: int) -> None:
    with db_cursor("auth") as (_conn, cursor):
        cursor.execute("DELETE FROM realmlist WHERE id = %s", (realm_id,))


def get_motd() -> str:
    try:
        with db_cursor("characters") as (_conn, cursor):
            _ensure_server_motd_table(cursor)
            cursor.execute("SELECT message FROM server_motd WHERE id = 1 LIMIT 1")
            row = cursor.fetchone()
            motd = str((row or {}).get("message") or "").strip()
            if motd:
                return motd
    except Exception:
        pass
    return str(CONFIG.get("worldserver", {}).get("motd", ""))


def save_motd(motd: str) -> None:
    normalized = str(motd or "").strip()
    with db_cursor("characters") as (_conn, cursor):
        _ensure_server_motd_table(cursor)
        cursor.execute(
            """
            INSERT INTO server_motd (id, message)
            VALUES (1, %s)
            ON DUPLICATE KEY UPDATE message = VALUES(message)
            """,
            (normalized,),
        )

    CONFIG.setdefault("worldserver", {})["motd"] = normalized


def _ensure_server_motd_table(cursor) -> None:
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS server_motd (
            id TINYINT UNSIGNED NOT NULL PRIMARY KEY,
            message TEXT NOT NULL
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
        """
    )


def save_motd_config_fallback(motd: str) -> None:
    try:
        with DEFAULT_CONFIG_PATH.open("r", encoding="utf-8") as handle:
            cfg = yaml.safe_load(handle) or {}
    except FileNotFoundError:
        cfg = {}

    worldserver_cfg = cfg.setdefault("worldserver", {})
    worldserver_cfg["motd"] = motd

    with DEFAULT_CONFIG_PATH.open("w", encoding="utf-8") as handle:
        yaml.safe_dump(cfg, handle, sort_keys=False, allow_unicode=True)

    CONFIG.setdefault("worldserver", {})["motd"] = motd
