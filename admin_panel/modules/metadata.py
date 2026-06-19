#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from __future__ import annotations

import struct

from admin_panel.modules.config import CLASS_NAMES, MAP_NAMES, PROJECT_ROOT, RACE_NAMES
from admin_panel.modules.db import fetch_all
from shared.PathUtils import get_dbc_root

ALLIANCE_RACES = {1, 3, 4, 7, 11, 22, 25}
HORDE_RACES = {2, 5, 6, 8, 9, 10, 26}
ICON_ROOT = PROJECT_ROOT / "admin_panel" / "static" / "icons"


def character_faction(race: int) -> str:
    if race in ALLIANCE_RACES:
        return "alliance"
    if race in HORDE_RACES:
        return "horde"
    return "neutral"


def faction_counts(rows: list[dict]) -> dict[str, int]:
    counts = {"alliance": 0, "horde": 0}

    for row in rows:
        faction = str(row.get("faction") or character_faction(int(row.get("race") or 0)))
        if faction in counts:
            counts[faction] += 1

    return counts


def icon_path(filename: str) -> str:
    return f"icons/{filename}" if (ICON_ROOT / filename).exists() else ""


def race_icon_path(race: int, gender: int) -> str:
    gender_icon = icon_path(f"{race}-{gender}.gif")
    if gender_icon:
        return gender_icon
    return icon_path(f"{race}.gif")


def class_icon_path(class_id: int) -> str:
    return icon_path(f"{class_id}.gif")


def faction_icon_path(faction: str) -> str:
    if faction == "alliance":
        return icon_path("allianceicon.gif") or icon_path("alliance.gif")
    if faction == "horde":
        return icon_path("hordeicon.gif") or icon_path("horde.gif")
    return ""


def map_name_lookup(map_ids: set[int]) -> dict[int, str]:
    if not map_ids:
        return {}

    names = {map_id: MAP_NAMES[map_id] for map_id in map_ids if map_id in MAP_NAMES}
    placeholders = ", ".join(["%s"] * len(map_ids))
    try:
        rows = fetch_all(
            "world",
            f"SELECT id, name FROM map WHERE id IN ({placeholders})",
            tuple(sorted(map_ids)),
        )
    except Exception:
        return names

    for row in rows:
        map_id = int(row["id"])
        name = str(row["name"] or "").strip()
        if name:
            names[map_id] = name
    return names


def zone_name_lookup(zone_ids: set[int]) -> dict[int, str]:
    if not zone_ids:
        return {}

    names: dict[int, str] = {}
    dbc_root = get_dbc_root()
    if dbc_root is None:
        return names

    path = dbc_root / "AreaTable.dbc"
    if not path.exists():
        return names

    try:
        with path.open("rb") as handle:
            if handle.read(4) != b"WDBC":
                return names
            record_count, field_count, record_size, string_size = struct.unpack("<4I", handle.read(16))
            records = [handle.read(record_size) for _ in range(record_count)]
            string_block = handle.read(string_size)
    except Exception:
        return names

    if field_count <= 13:
        return names

    for record in records:
        if len(record) != record_size:
            continue
        area_id = struct.unpack_from("<I", record, 0)[0]
        if area_id not in zone_ids:
            continue
        name_offset = struct.unpack_from("<I", record, 13 * 4)[0]
        if name_offset <= 0 or name_offset >= len(string_block):
            continue
        end = string_block.find(b"\x00", name_offset)
        if end < 0:
            end = len(string_block)
        name = string_block[name_offset:end].decode("utf-8", errors="ignore").strip()
        if name:
            names[int(area_id)] = name
    return names


def enrich_character_rows(rows: list[dict]) -> list[dict]:
    map_names = map_name_lookup({int(row.get("map") or 0) for row in rows})
    zone_names = zone_name_lookup({int(row.get("zone") or 0) for row in rows})

    for row in rows:
        race = int(row.get("race") or 0)
        gender = int(row.get("gender") or 0)
        class_id = int(row.get("class_id") or 0)
        map_id = int(row.get("map") or 0)
        zone_id = int(row.get("zone") or 0)
        faction = character_faction(race)
        row["race_name"] = RACE_NAMES.get(race, f"Race {race}")
        row["class_name"] = CLASS_NAMES.get(class_id, f"Class {class_id}")
        row["map_name"] = map_names.get(map_id, f"Map {map_id}")
        row["zone_name"] = zone_names.get(zone_id, f"Zone {zone_id}") if zone_id else ""
        if row["zone_name"] == row["map_name"]:
            row["zone_name"] = ""
        row["location_name"] = (
            f"{row['map_name']}: {row['zone_name']}"
            if row["zone_name"]
            else row["map_name"]
        )
        row["faction"] = faction
        row["race_icon"] = race_icon_path(race, gender)
        row["class_icon"] = class_icon_path(class_id)
        row["faction_icon"] = faction_icon_path(faction)
        if "account" in row:
            row["account_name"] = row.get("account_name") or f"Account {row.get('account')}"
    return rows
