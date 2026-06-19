#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from __future__ import annotations

from admin_panel.modules.db import fetch_all

LOOKUP_KINDS = {
    "items": "Items",
    "npcs": "NPCs",
    "gameobjects": "Game Objects",
}
DEFAULT_LOOKUP_LIMIT = 100


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
        return fetch_all(
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
        )
    return fetch_all(
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
    )
