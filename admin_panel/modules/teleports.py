#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from __future__ import annotations

from admin_panel.modules.db import db_cursor, fetch_all
from admin_panel.modules.forms import as_float, as_int, as_text
from admin_panel.modules.metadata import map_name_lookup

TELEPORT_CACHE: list[dict] = []
TELEPORT_CACHE_LOADED = False


def load_teleport_cache() -> list[dict]:
    global TELEPORT_CACHE, TELEPORT_CACHE_LOADED
    rows = fetch_all(
        "world",
        """
        SELECT name, map, position_x, position_y, position_z, orientation
        FROM game_tele
        ORDER BY name ASC
        """,
    )
    map_names = map_name_lookup({int(row.get("map") or 0) for row in rows})
    for row in rows:
        map_id = int(row.get("map") or 0)
        row["map_name"] = map_names.get(map_id, f"Map {map_id}")
    TELEPORT_CACHE = rows
    TELEPORT_CACHE_LOADED = True
    return TELEPORT_CACHE


def warm_teleport_cache() -> None:
    try:
        load_teleport_cache()
    except Exception:
        # Startup must survive an offline external MySQL server.
        pass


def teleport_rows() -> list[dict]:
    if not TELEPORT_CACHE_LOADED:
        warm_teleport_cache()
    return [dict(row) for row in TELEPORT_CACHE]


def teleport_count() -> int:
    return len(teleport_rows())


def get_teleport(name: str) -> dict | None:
    normalized = str(name or "").strip().lower()
    for row in teleport_rows():
        if str(row.get("name") or "").strip().lower() == normalized:
            return row
    return None


def save_teleport(old_name: str | None = None) -> str:
    name = as_text("name")
    if not name:
        raise ValueError("Teleport name is required.")

    with db_cursor("world") as (_conn, cursor):
        if old_name:
            cursor.execute("DELETE FROM game_tele WHERE LOWER(name) = LOWER(%s)", (old_name,))
        else:
            cursor.execute("DELETE FROM game_tele WHERE LOWER(name) = LOWER(%s)", (name,))
        cursor.execute(
            """
            INSERT INTO game_tele (name, map, position_x, position_y, position_z, orientation)
            VALUES (%s, %s, %s, %s, %s, %s)
            """,
            (
                name,
                as_int("map"),
                as_float("position_x"),
                as_float("position_y"),
                as_float("position_z"),
                as_float("orientation"),
            ),
        )
    load_teleport_cache()
    return name


def delete_teleport(name: str) -> None:
    with db_cursor("world") as (_conn, cursor):
        cursor.execute("DELETE FROM game_tele WHERE LOWER(name) = LOWER(%s)", (name,))
    load_teleport_cache()
