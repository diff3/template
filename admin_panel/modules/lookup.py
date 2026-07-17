#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from __future__ import annotations

from functools import lru_cache
from pathlib import Path
import re

from admin_panel.modules.db import fetch_all
from server.modules.dbc import read_dbc

LOOKUP_KINDS = {
    "items": "Items",
    "npcs": "NPCs",
    "gameobjects": "Game Objects",
}
DEFAULT_LOOKUP_LIMIT = 100
ITEM_ICON_CDN = "https://wow.zamimg.com/images/wow/icons/large"
_ITEM_DISPLAY_INFO_DBC = Path(__file__).resolve().parents[2] / "data" / "client" / "dbc" / "ItemDisplayInfo.dbc"
_ITEM_DISPLAY_INFO_FMT = "nssssss" + ("x" * 19)
_SAFE_ICON_NAME = re.compile(r"^[A-Za-z0-9_-]+$")
ITEM_QUALITY_NAMES = {
    0: "Poor",
    1: "Common",
    2: "Uncommon",
    3: "Rare",
    4: "Epic",
    5: "Legendary",
    6: "Artifact",
    7: "Heirloom",
}


@lru_cache(maxsize=1)
def _item_icon_names() -> dict[int, str]:
    if not _ITEM_DISPLAY_INFO_DBC.exists():
        return {}
    icons: dict[int, str] = {}
    for row in read_dbc(_ITEM_DISPLAY_INFO_DBC, _ITEM_DISPLAY_INFO_FMT):
        display_id = int(row[0] or 0)
        icon_name = str(row[5] or row[6] or "").strip()
        if display_id > 0 and _SAFE_ICON_NAME.fullmatch(icon_name):
            icons[display_id] = icon_name.lower()
    return icons


def _add_item_icons(rows: list[dict]) -> list[dict]:
    icons = _item_icon_names()
    for row in rows:
        icon_name = icons.get(int(row.get("visual_id") or 0), "inv_misc_questionmark")
        quality = int(row.get("quality") or 0)
        row["icon_name"] = icon_name
        row["icon_url"] = f"{ITEM_ICON_CDN}/{icon_name}.jpg"
        row["quality_name"] = ITEM_QUALITY_NAMES.get(quality, f"Unknown ({quality})")
    return rows


def normalize_lookup_kind(value: str | None) -> str:
    kind = str(value or "").strip().lower()
    return kind if kind in LOOKUP_KINDS else "items"


def _search_pattern(query: str) -> str:
    return f"%{query.strip()}%"


def lookup_rows(kind: str, query: str, *, limit: int = DEFAULT_LOOKUP_LIMIT) -> list[dict]:
    kind = normalize_lookup_kind(kind)
    query = str(query or "").strip()
    if not query:
        return []

    limit = max(1, min(int(limit), 250))
    numeric_id = int(query) if query.isdigit() else None

    if kind == "npcs":
        if numeric_id is not None:
            return fetch_all(
                "world",
                """
                SELECT
                    entry AS id,
                    name,
                    modelid1 AS visual_id,
                    subname
                FROM creature_template
                WHERE name LIKE %s OR entry = %s OR modelid1 = %s
                ORDER BY
                    CASE WHEN entry = %s THEN 0 ELSE 1 END,
                    name ASC,
                    entry ASC
                LIMIT %s
                """,
                (_search_pattern(query), numeric_id, numeric_id, numeric_id, limit),
            )
        return fetch_all(
            "world",
            """
            SELECT
                entry AS id,
                name,
                modelid1 AS visual_id,
                subname
            FROM creature_template
            WHERE name LIKE %s
            ORDER BY name ASC, entry ASC
            LIMIT %s
            """,
            (_search_pattern(query), limit),
        )

    if kind == "gameobjects":
        if numeric_id is not None:
            return fetch_all(
                "world",
                """
                SELECT
                    entry AS id,
                    name,
                    displayId AS visual_id,
                    type,
                    IconName AS icon_name
                FROM gameobject_template
                WHERE name LIKE %s OR entry = %s OR displayId = %s
                ORDER BY
                    CASE WHEN entry = %s THEN 0 ELSE 1 END,
                    name ASC,
                    entry ASC
                LIMIT %s
                """,
                (_search_pattern(query), numeric_id, numeric_id, numeric_id, limit),
            )
        return fetch_all(
            "world",
            """
            SELECT
                entry AS id,
                name,
                displayId AS visual_id,
                type,
                IconName AS icon_name
            FROM gameobject_template
            WHERE name LIKE %s
            ORDER BY name ASC, entry ASC
            LIMIT %s
            """,
            (_search_pattern(query), limit),
        )

    if numeric_id is not None:
        return _add_item_icons(fetch_all(
            "world",
            """
            SELECT
                entry AS id,
                name,
                displayid AS visual_id,
                Quality AS quality,
                InventoryType AS inventory_type
            FROM item_template
            WHERE name LIKE %s OR entry = %s OR displayid = %s
            ORDER BY
                CASE WHEN entry = %s THEN 0 ELSE 1 END,
                name ASC,
                entry ASC
            LIMIT %s
            """,
            (_search_pattern(query), numeric_id, numeric_id, numeric_id, limit),
        ))
    return _add_item_icons(fetch_all(
        "world",
        """
        SELECT
            entry AS id,
            name,
            displayid AS visual_id,
            Quality AS quality,
            InventoryType AS inventory_type
        FROM item_template
        WHERE name LIKE %s
        ORDER BY name ASC, entry ASC
        LIMIT %s
        """,
        (_search_pattern(query), limit),
    ))
