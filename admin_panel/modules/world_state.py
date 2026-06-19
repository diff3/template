#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from __future__ import annotations

import json
import time
from typing import Any

from admin_panel.modules.db import fetch_all
from admin_panel.modules.metadata import map_name_lookup
from shared.PathUtils import get_data_root
from server.modules.handlers.world.state.weather_zone_registry import canonical_weather_zone_registry
from server.modules.dbc import read_dbc


TRANSPORT_GROUPS = (
    ("boats", "Boats"),
    ("zeppelins", "Zeppelins"),
    ("elevators", "Elevators"),
)

ELEVATOR_ENTRIES = {
    20649,
    20652,
    20655,
    4170,
    4171,
    11898,
    11899,
    47296,
    47297,
}

ELEVATOR_NAME_OVERRIDES = {
    20649: "Undercity Elevator 1",
    20652: "Undercity Elevator 2",
    20655: "Undercity Elevator 3",
    4170: "Thunder Bluff Elevator",
    4171: "Thunder Bluff Elevator",
    11898: "Thunder Bluff Elevator",
    11899: "Thunder Bluff Elevator",
    47296: "Thunder Bluff Elevator",
    47297: "Thunder Bluff Elevator",
    183169: "Shattrath Elevator 1",
    183202: "Shattrath Elevator 2",
    183203: "Shattrath Elevator 3",
    206608: "Orgrimmar Elevator 1",
    206609: "Orgrimmar Elevator 2",
    206610: "Orgrimmar Elevator 3",
    219175: "Orgrimmar Elevator 1",
    219176: "Orgrimmar Elevator 2",
    219177: "Orgrimmar Elevator 3",
    220364: "Orgrimmar Elevator 4",
}

KNOWN_ROUTE_NAMES = {
    176231: "Menethil Harbor ⇄ Theramore",
    176244: "Teldrassil ⇄ Auberdine",
    176310: "Stormwind ⇄ Auberdine",
    176495: "Grom'gol ⇄ Orgrimmar",
    177233: "Feathermoon Ferry",
    181646: "Azuremyst Isle ⇄ Auberdine",
    181688: "Valaar's Berth ⇄ Auberdine",
    186238: "Orgrimmar ⇄ Undercity",
    20808: "Ratchet ⇄ Booty Bay",
}

ROUTE_ENDPOINT_MAPS = {
    "Auberdine": 1,
    "Azuremyst Isle": 530,
    "Booty Bay": 0,
    "Grom'gol": 0,
    "Menethil Harbor": 0,
    "Orgrimmar": 1,
    "Ratchet": 1,
    "Stormwind": 0,
    "Teldrassil": 1,
    "Theramore": 1,
    "Thunder Bluff": 1,
    "Undercity": 0,
    "Valaar's Berth": 530,
}

WEATHER_ICONS = {
    "Clear": "☀",
    "Rain": "🌦",
    "Heavy Rain": "🌧",
    "Snow": "❄",
    "Storm": "⛈",
    "Fog": "🌫",
    "Unknown": "🌍",
}


def world_dashboard() -> dict[str, Any]:
    snapshot = _load_runtime_snapshot()
    transports = _transport_rows(snapshot)
    weather = _weather_rows(snapshot)
    search_results = _world_search_results(transports, weather)
    generated_at = int(snapshot.get("generated_at", 0) or 0)
    return {
        "transports": transports,
        "transport_groups": _group_transports(transports),
        "weather": weather,
        "search_results": search_results,
        "transport_count": len(transports),
        "weather_count": len(weather),
        "search_result_count": len(search_results),
        "generated_at": _format_generated_at(generated_at),
        "generated_time": _format_generated_time(generated_at),
        "generated_at_epoch": generated_at,
        "snapshot_available": bool(snapshot),
    }


def _load_runtime_snapshot() -> dict[str, Any]:
    path = get_data_root() / "runtime" / "world_state.json"
    if not path.exists():
        return {}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}
    return data if isinstance(data, dict) else {}


def _transport_rows(snapshot: dict[str, Any]) -> list[dict[str, Any]]:
    rows = [
        dict(row)
        for row in snapshot.get("transports", [])
        if isinstance(row, dict)
    ]
    map_names = map_name_lookup({
        _as_int(row.get("map_id"))
        for row in rows
        if _as_int(row.get("map_id")) >= 0
    })
    metadata = _transport_metadata(rows)
    path_names = _taxi_path_route_names({
        _as_int(item.get("path_id"))
        for item in metadata.values()
        if _as_int(item.get("path_id")) > 0
    })

    for row in rows:
        map_id = _as_int(row.get("map_id"))
        row["map_name"] = map_names.get(map_id, f"Map {map_id}") if map_id >= 0 else ""
        meta = _metadata_for_row(row, metadata)
        row["category"] = _transport_category(row, meta)
        row["category_label"] = _category_label(str(row["category"]))
        title, label_source = _transport_title_with_source(row, meta, path_names)
        row["name"] = title
        row["label_source"] = label_source
        row["path_id"] = _as_int(meta.get("path_id"))
        row["status_label"] = _status_label(row)
        row["status_class"] = _status_class(str(row["status_label"]))
        row["phase_percent"] = _phase_percent(
            _as_int(row.get("phase_ms")),
            _as_int(row.get("period_ms")),
        )
        row["phase_label"] = f"Phase {row['phase_percent']}%"
        row["phase_seconds"] = _phase_seconds_label(
            _as_int(row.get("phase_ms")),
            _as_int(row.get("period_ms")),
        )
        row["location_name"] = _location_name(row)
        row["location_detail"] = _location_detail(row)
        row["passenger_label"] = _passenger_label(_as_int(row.get("passenger_count")))
        row["position_label"] = _position_label(row)
        row["copy_command"] = _copy_command(row)
        row["meta_name"] = str(meta.get("name", "") or "")
        row["meta_object_type"] = _metadata_object_type(meta)
        row["metadata_map_id"] = _as_int(meta.get("map_id"))
        row["metadata_display_id"] = _as_int(meta.get("display_id"))
        row["search_text"] = _transport_search_text(row)

    rows = _dedupe_synced_elevator_rows(rows)
    rows.sort(key=lambda item: (
        _category_order(str(item.get("category", ""))),
        str(item.get("name", "")).lower(),
        _as_int(item.get("entry")),
        _as_int(item.get("world_guid")),
    ))
    return rows


def _group_transports(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    groups: list[dict[str, Any]] = []
    for key, label in TRANSPORT_GROUPS:
        transports = [
            row
            for row in rows
            if str(row.get("category", "")) == key
        ]
        groups.append({
            "key": key,
            "label": label,
            "count": len(transports),
            "transports": transports,
        })
    return groups


def _dedupe_synced_elevator_rows(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    grouped: dict[tuple[int, int, int, int], list[dict[str, Any]]] = {}
    result: list[dict[str, Any]] = []
    for row in rows:
        if str(row.get("category") or "") != "elevators":
            result.append(row)
            continue
        key = (
            _as_int(row.get("map_id")),
            _as_int(row.get("metadata_display_id") or row.get("display_id")),
            int(round(float(row.get("x", 0.0) or 0.0) * 10.0)),
            int(round(float(row.get("y", 0.0) or 0.0) * 10.0)),
        )
        grouped.setdefault(key, []).append(row)

    for group in grouped.values():
        selected = _preferred_synced_elevator_row(group)
        if len(group) > 1:
            selected = dict(selected)
            selected["synced_variant_count"] = len(group)
            selected["search_text"] = _transport_search_text(selected)
        result.append(selected)
    return result


def _preferred_synced_elevator_row(rows: list[dict[str, Any]]) -> dict[str, Any]:
    return sorted(
        rows,
        key=lambda row: (
            _as_int(row.get("metadata_map_id")) != _as_int(row.get("map_id")),
            _as_int(row.get("entry")),
            _as_int(row.get("world_guid")),
        ),
    )[0]


def _world_search_results(
    transports: list[dict[str, Any]],
    weather: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    return (
        _weather_search_results(weather)
        + _transport_search_results(transports)
        + _teleport_search_results()
        + _zone_search_results(weather)
        + _continent_search_results(weather)
        + _command_search_results()
    )


def _search_result(
    result_type: str,
    title: str,
    subtitle: str,
    action: dict[str, Any] | None,
    metadata: dict[str, Any] | None,
    *search_parts: Any,
    icon: str = "",
) -> dict[str, Any]:
    row = {
        "type": str(result_type),
        "title": str(title or "").strip(),
        "subtitle": str(subtitle or "").strip(),
        "action": dict(action or {"kind": "none"}),
        "metadata": dict(metadata or {}),
        "icon": str(icon or ""),
    }
    row["search_text"] = _normalized_search_text(
        row["type"],
        row["title"],
        row["subtitle"],
        *search_parts,
    )
    return row


def _weather_search_results(weather: list[dict[str, Any]]) -> list[dict[str, Any]]:
    results: list[dict[str, Any]] = []
    for row in weather:
        zone_name = str(row.get("zone_name") or "").strip()
        if not zone_name:
            continue
        results.append(_search_result(
            "weather",
            zone_name,
            str(row.get("current") or "Unknown"),
            {
                "kind": "copy",
                "label": "Copy Teleport",
                "command": f".tele {row.get('teleport_name') or zone_name}",
            },
            {
                "zone": _as_int(row.get("zone")),
                "map": _as_int(row.get("map_id")),
                "map_name": row.get("map_name"),
                "continent": row.get("continent_name"),
                "weather": row.get("current"),
            },
            row.get("search_text"),
            icon=str(row.get("weather_icon") or WEATHER_ICONS["Unknown"]),
        ))
    return results


def _transport_search_results(transports: list[dict[str, Any]]) -> list[dict[str, Any]]:
    results: list[dict[str, Any]] = []
    for row in transports:
        title = str(row.get("name") or "").strip()
        if not title:
            continue
        subtitle_parts = [
            str(row.get("status_label") or "").strip(),
            str(row.get("passenger_label") or "").strip(),
            str(row.get("phase_label") or "").strip(),
        ]
        subtitle = " · ".join(part for part in subtitle_parts if part)
        action = {"kind": "none"}
        if str(row.get("copy_command") or "").strip():
            action = {
                "kind": "copy",
                "label": "Copy Position",
                "command": str(row.get("copy_command")),
            }
        results.append(_search_result(
            "transport",
            title,
            subtitle,
            action,
            {
                "entry": _as_int(row.get("entry")),
                "world_guid": _as_int(row.get("world_guid")),
                "spawn_guid": _as_int(row.get("spawn_guid")),
                "map": _as_int(row.get("map_id")),
                "map_name": row.get("map_name"),
                "category": row.get("category"),
                "status": row.get("status_label"),
            },
            row.get("search_text"),
            icon=_transport_result_icon(str(row.get("category") or "")),
        ))
    return results


def _teleport_search_results() -> list[dict[str, Any]]:
    try:
        rows = _teleport_rows_for_search()
    except Exception:
        rows = []

    results: list[dict[str, Any]] = []
    for row in rows:
        name = str(row.get("name") or "").strip()
        if not name:
            continue
        map_id = _as_int(row.get("map"))
        map_name = str(row.get("map_name") or f"Map {map_id}")
        results.append(_search_result(
            "teleport",
            name,
            map_name,
            {
                "kind": "copy",
                "label": "Copy Teleport",
                "command": f".tele {name}",
            },
            {
                "map": map_id,
                "map_name": map_name,
                "position_x": row.get("position_x"),
                "position_y": row.get("position_y"),
                "position_z": row.get("position_z"),
            },
            map_name,
            _continent_name(map_id, map_name),
            icon="⌖",
        ))
    return results


def _zone_search_results(weather: list[dict[str, Any]]) -> list[dict[str, Any]]:
    results: list[dict[str, Any]] = []
    seen: set[int] = set()
    for row in weather:
        zone_id = _as_int(row.get("zone"))
        zone_name = str(row.get("zone_name") or "").strip()
        if zone_id <= 0 or not zone_name or zone_id in seen:
            continue
        seen.add(zone_id)
        results.append(_search_result(
            "zone",
            zone_name,
            str(row.get("continent_name") or row.get("map_name") or ""),
            {
                "kind": "copy",
                "label": "Copy Teleport",
                "command": f".tele {row.get('teleport_name') or zone_name}",
            },
            {
                "zone": zone_id,
                "map": _as_int(row.get("map_id")),
                "map_name": row.get("map_name"),
                "continent": row.get("continent_name"),
            },
            row.get("normalized_name"),
            " ".join(row.get("search_aliases") or []),
            row.get("search_text"),
            icon="◇",
        ))
    return results


def _continent_search_results(weather: list[dict[str, Any]]) -> list[dict[str, Any]]:
    by_map: dict[int, dict[str, Any]] = {}
    for row in weather:
        map_id = _as_int(row.get("map_id"))
        if map_id < 0 or map_id in by_map:
            continue
        continent = str(row.get("continent_name") or row.get("map_name") or "").strip()
        if not continent:
            continue
        by_map[map_id] = row

    results: list[dict[str, Any]] = []
    for map_id, row in sorted(by_map.items(), key=lambda item: str(item[1].get("continent_name") or "").lower()):
        continent = str(row.get("continent_name") or row.get("map_name") or "")
        results.append(_search_result(
            "continent",
            continent,
            "Runtime weather map",
            {
                "kind": "section",
                "label": "Show Weather",
                "target": "weather",
            },
            {
                "map": map_id,
                "map_name": row.get("map_name"),
                "continent": continent,
            },
            " ".join(_continent_search_aliases(map_id, continent)),
            icon="◎",
        ))
    return results


def _command_search_results() -> list[dict[str, Any]]:
    try:
        rows = _command_rows_for_search()
    except Exception:
        rows = []

    results: list[dict[str, Any]] = []
    for row in rows:
        name = str(row.get("name") or "").strip()
        if not name:
            continue
        usage = str(row.get("usage") or name)
        results.append(_search_result(
            "command",
            name,
            usage,
            {
                "kind": "copy",
                "label": "Copy Command",
                "command": usage,
            },
            {
                "allow_args": bool(row.get("allow_args")),
                "require_args": bool(row.get("require_args")),
            },
            " ".join(row.get("aliases") or []),
            icon="/",
        ))
    return results


def _teleport_rows_for_search() -> list[dict[str, Any]]:
    from admin_panel.modules.teleports import teleport_rows

    return teleport_rows()


def _command_rows_for_search() -> list[dict[str, Any]]:
    from admin_panel.modules.commands import command_rows

    return command_rows()


def _transport_metadata(rows: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    entry_ids = {
        _as_int(row.get("entry"))
        for row in rows
        if _as_int(row.get("entry")) > 0
    }
    spawn_guids = set()
    for row in rows:
        spawn_guid = _as_int(row.get("spawn_guid"))
        if spawn_guid > 0:
            spawn_guids.add(spawn_guid)
            spawn_guids.add(spawn_guid % 100000)

    if not entry_ids and not spawn_guids:
        return {}

    cache_key = (tuple(sorted(entry_ids)), tuple(sorted(spawn_guids)))
    cached = getattr(_transport_metadata, "_cache", None)
    if (
        isinstance(cached, tuple)
        and len(cached) == 3
        and cached[0] == cache_key
        and time.monotonic() < float(cached[1]) + 60.0
    ):
        return dict(cached[2])

    transport_clauses: list[str] = []
    gameobject_clauses: list[str] = []
    params: list[int] = []
    gameobject_params: list[int] = []
    if entry_ids:
        placeholders = ", ".join(["%s"] * len(entry_ids))
        transport_clauses.append(f"t.entry IN ({placeholders})")
        gameobject_clauses.append(f"gt.entry IN ({placeholders})")
        sorted_entries = sorted(entry_ids)
        params.extend(sorted_entries)
        gameobject_params.extend(sorted_entries)
    if spawn_guids:
        placeholders = ", ".join(["%s"] * len(spawn_guids))
        transport_clauses.append(f"t.guid IN ({placeholders})")
        gameobject_clauses.append(f"g.guid IN ({placeholders})")
        sorted_guids = sorted(spawn_guids)
        params.extend(sorted_guids)
        gameobject_params.extend(sorted_guids)

    try:
        db_rows = fetch_all(
            "world",
            f"""
            SELECT
                'transport' AS source,
                t.guid,
                t.entry,
                t.name,
                gt.name AS template_name,
                gt.data0 AS path_id,
                gt.displayId AS display_id,
                gt.type AS object_type,
                NULL AS map_id,
                NULL AS x,
                NULL AS y,
                NULL AS z
            FROM transports t
            LEFT JOIN gameobject_template gt ON gt.entry = t.entry
            WHERE {" OR ".join(transport_clauses)}
            UNION ALL
            SELECT
                'gameobject' AS source,
                g.guid,
                gt.entry,
                NULL AS name,
                gt.name AS template_name,
                gt.data0 AS path_id,
                gt.displayId AS display_id,
                gt.type AS object_type,
                g.map AS map_id,
                g.position_x AS x,
                g.position_y AS y,
                g.position_z AS z
            FROM gameobject_template gt
            LEFT JOIN gameobject g ON g.id = gt.entry
            WHERE gt.type IN (11, 15)
              AND ({" OR ".join(gameobject_clauses)})
            """,
            tuple(params + gameobject_params),
        )
    except Exception:
        return {}

    metadata: dict[str, dict[str, Any]] = {}
    for item in db_rows:
        row = dict(item)
        entry = _as_int(row.get("entry"))
        guid = _as_int(row.get("guid"))
        if entry > 0:
            _store_transport_metadata(metadata, f"entry:{entry}", row)
        if guid > 0:
            _store_transport_metadata(metadata, f"guid:{guid}", row)
    setattr(_transport_metadata, "_cache", (cache_key, time.monotonic(), dict(metadata)))
    return metadata


def _store_transport_metadata(
    metadata: dict[str, dict[str, Any]],
    key: str,
    row: dict[str, Any],
) -> None:
    existing = metadata.get(key)
    if existing is None:
        metadata[key] = row
        return

    existing_source = str(existing.get("source") or "")
    source = str(row.get("source") or "")
    if existing_source == "transport":
        return
    if source == "transport":
        metadata[key] = row
        return
    if _as_int(existing.get("guid")) <= 0 and _as_int(row.get("guid")) > 0:
        metadata[key] = row


def _metadata_for_row(
    row: dict[str, Any],
    metadata: dict[str, dict[str, Any]],
) -> dict[str, Any]:
    spawn_guid = _as_int(row.get("spawn_guid"))
    for key in (
        f"guid:{spawn_guid}",
        f"guid:{spawn_guid % 100000}" if spawn_guid > 0 else "",
        f"entry:{_as_int(row.get('entry'))}",
    ):
        if key and key in metadata:
            return metadata[key]
    return {}


def _taxi_path_route_names(path_ids: set[int]) -> dict[int, str]:
    if not path_ids:
        return {}

    cached = getattr(_taxi_path_route_names, "_cache", None)
    if isinstance(cached, dict):
        return {
            path_id: cached[path_id]
            for path_id in path_ids
            if path_id in cached
        }

    try:
        from shared.PathUtils import get_dbc_root

        dbc_root = get_dbc_root()
    except Exception:
        dbc_root = None
    if dbc_root is None:
        dbc_root = get_data_root() / "client" / "dbc"

    taxi_path_file = dbc_root / "TaxiPath.dbc"
    taxi_nodes_file = dbc_root / "TaxiNodes.dbc"
    if not taxi_path_file.exists() or not taxi_nodes_file.exists():
        setattr(_taxi_path_route_names, "_cache", {})
        return {}

    try:
        path_rows = read_dbc(taxi_path_file, "diii")
        node_rows = read_dbc(taxi_nodes_file, "difffsiixxxx")
    except Exception:
        setattr(_taxi_path_route_names, "_cache", {})
        return {}

    node_names = {
        _as_int(record[0]): _clean_endpoint_name(str(record[5] or ""))
        for record in node_rows
        if _as_int(record[0]) > 0
    }

    all_names: dict[int, str] = {}
    for record in path_rows:
        path_id = _as_int(record[0])
        source = node_names.get(_as_int(record[1]), "")
        destination = node_names.get(_as_int(record[2]), "")
        if source and destination:
            all_names[path_id] = f"{source} ⇄ {destination}"
    setattr(_taxi_path_route_names, "_cache", dict(all_names))
    return {
        path_id: all_names[path_id]
        for path_id in path_ids
        if path_id in all_names
    }


def _transport_title(
    row: dict[str, Any],
    metadata: dict[str, Any],
    path_names: dict[int, str],
) -> str:
    return _transport_title_with_source(row, metadata, path_names)[0]


def _transport_title_with_source(
    row: dict[str, Any],
    metadata: dict[str, Any],
    path_names: dict[int, str],
) -> tuple[str, str]:
    entry = _as_int(row.get("entry"))
    if _metadata_object_type(metadata) == 11 or entry in ELEVATOR_NAME_OVERRIDES:
        elevator_name = _elevator_title(row, metadata)
        if elevator_name:
            return elevator_name, "elevator"

    path_id = _as_int(metadata.get("path_id"))
    taxi_path_name = str(path_names.get(path_id, "") or "").strip()
    if taxi_path_name:
        return taxi_path_name, "taxi_path"

    transport_name = _metadata_transport_label(str(metadata.get("name") or ""))
    if transport_name:
        return transport_name, "transports_table"

    template_name = _metadata_transport_label(str(metadata.get("template_name") or ""))
    if template_name:
        return template_name, "template_name"

    if entry in KNOWN_ROUTE_NAMES:
        return KNOWN_ROUTE_NAMES[entry], "known_override"

    return f"Transport {entry}", "fallback"


def _metadata_transport_label(value: str) -> str:
    name = _clean_transport_name(value)
    if not name:
        return ""

    quoted_name = _quoted_transport_name(name)
    if quoted_name and "ferry" in quoted_name.lower():
        return quoted_name

    route_name = _route_name_from_transport_metadata(name)
    if route_name:
        return route_name
    if quoted_name:
        return quoted_name
    return name


def _quoted_transport_name(value: str) -> str:
    text = str(value or "")
    start = text.rfind("(\"")
    end = text.rfind("\")")
    if start >= 0 and end > start:
        return text[start + 2:end].strip()

    first = text.find("\"")
    last = text.rfind("\"")
    if first >= 0 and last > first:
        return text[first + 1:last].strip()
    return ""


def _route_name_from_transport_metadata(value: str) -> str:
    text = str(value or "").split("(\"", 1)[0].strip()
    parts = [part.strip() for part in text.split(" and ") if part.strip()]
    if len(parts) != 2:
        return ""

    source = _metadata_route_endpoint(parts[0])
    destination = _metadata_route_endpoint(parts[1])
    if not source or not destination:
        return ""
    if source.lower() == destination.lower():
        return ""
    return f"{source} ⇄ {destination}"


def _metadata_route_endpoint(value: str) -> str:
    parts = [part.strip() for part in str(value or "").split(",") if part.strip()]
    if not parts:
        return ""
    first = parts[0]
    if len(parts) > 1 and "ports" in first.lower():
        return parts[1]
    return first


def _transport_category(row: dict[str, Any], metadata: dict[str, Any]) -> str:
    entry = _as_int(row.get("entry"))
    object_type = _metadata_object_type(metadata)
    if object_type == 11 or entry in ELEVATOR_ENTRIES or entry in ELEVATOR_NAME_OVERRIDES:
        return "elevators"
    if object_type == 15:
        text = " ".join(
            str(value or "")
            for value in (
                metadata.get("name"),
                metadata.get("template_name"),
                row.get("name"),
            )
        ).lower()
        if any(token in text for token in ("zeppelin", "the thundercaller", "cloudkisser")):
            return "zeppelins"
        return "boats"

    text = " ".join(
        str(value or "")
        for value in (
            metadata.get("name"),
            metadata.get("template_name"),
            row.get("name"),
        )
    ).lower()

    if any(token in text for token in ("elevator", "lift")):
        return "elevators"
    if any(token in text for token in ("zeppelin", "the thundercaller", "cloudkisser")):
        return "zeppelins"
    if entry in {176495, 186238}:
        return "zeppelins"
    return "boats"


def _metadata_object_type(metadata: dict[str, Any]) -> int:
    return _as_int(
        metadata.get("object_type")
        if metadata.get("object_type") is not None
        else metadata.get("type")
    )


def _elevator_title(row: dict[str, Any], metadata: dict[str, Any]) -> str:
    entry = _as_int(row.get("entry"))
    if entry in ELEVATOR_NAME_OVERRIDES:
        return ELEVATOR_NAME_OVERRIDES[entry]

    template_name = _clean_transport_name(str(metadata.get("template_name") or ""))
    lowered = template_name.lower()
    if "undervator" in lowered:
        return "Undercity Elevator"
    if "mesa elevator" in lowered:
        return "Thunder Bluff Elevator"
    if "ancdrae_elevator" in lowered:
        return "Shattrath Elevator"
    if "orgrimmar_elevator" in lowered:
        return "Orgrimmar Elevator"
    if "elevator" in lowered or "lift" in lowered:
        return template_name
    return f"Elevator {entry}"


def _status_label(row: dict[str, Any]) -> str:
    lifecycle = str(row.get("lifecycle_state") or "").upper()
    visibility = str(row.get("visibility_state") or "").upper()
    if visibility == "TRANSFERRING" or lifecycle in {"TRANSFER_PENDING", "TRANSFERRING"}:
        return "Transferring"
    if lifecycle in {"DOCKED", "WAITING"} or visibility == "WAITING":
        return "Docked"
    return "En Route"


def _status_class(label: str) -> str:
    if label == "Docked":
        return "status-docked"
    if label == "Transferring":
        return "status-transferring"
    return "status-active"


def _location_name(row: dict[str, Any]) -> str:
    map_name = str(row.get("map_name", "") or "").strip()
    if map_name:
        return map_name
    return f"Map {_as_int(row.get('map_id'))}"


def _location_detail(row: dict[str, Any]) -> str:
    endpoint = _route_endpoint_for_map(
        str(row.get("name", "") or ""),
        _as_int(row.get("map_id")),
    )
    map_name = str(row.get("map_name", "") or "").strip()
    if endpoint:
        return endpoint
    if not map_name:
        return ""
    return ""


def _route_endpoint_for_map(route_name: str, map_id: int) -> str:
    endpoints = [
        part.strip()
        for part in str(route_name or "").split("⇄")
        if part.strip()
    ]
    matches = [
        endpoint
        for endpoint in endpoints
        if ROUTE_ENDPOINT_MAPS.get(endpoint) == int(map_id)
    ]
    if len(matches) == 1:
        return matches[0]
    return ""


def _phase_seconds_label(phase_ms: int, period_ms: int) -> str:
    if int(period_ms) <= 0:
        return ""
    return f"{int(round(phase_ms / 1000.0))}s / {int(round(period_ms / 1000.0))}s"


def _passenger_label(count: int) -> str:
    return "Passenger" if int(count) == 1 else "Passengers"


def _position_label(row: dict[str, Any]) -> str:
    try:
        return "{:.1f}, {:.1f}, {:.1f}".format(
            float(row.get("x")),
            float(row.get("y")),
            float(row.get("z")),
        )
    except (TypeError, ValueError):
        return ""


def _copy_command(row: dict[str, Any]) -> str:
    if not _position_label(row):
        return ""
    return ".tel coord {} {:.2f} {:.2f} {:.2f} {:.2f}".format(
        _as_int(row.get("map_id")),
        float(row.get("x", 0.0) or 0.0),
        float(row.get("y", 0.0) or 0.0),
        float(row.get("z", 0.0) or 0.0),
        float(row.get("orientation", 0.0) or 0.0),
    )


def _clean_transport_name(value: str) -> str:
    name = str(value or "").strip()
    prefixes = ("Transport, ", "Transport: ")
    for prefix in prefixes:
        if name.startswith(prefix):
            name = name[len(prefix):].strip()
    return name


def _clean_endpoint_name(value: str) -> str:
    name = str(value or "").strip()
    for marker in (" - ", ", "):
        if marker in name:
            name = name.split(marker, 1)[0].strip()
    return name


def _category_label(key: str) -> str:
    return dict(TRANSPORT_GROUPS).get(str(key), "Boats")


def _category_singular(key: str) -> str:
    if key == "elevators":
        return "Elevator"
    if key == "zeppelins":
        return "Zeppelin"
    return "Boat"


def _category_order(key: str) -> int:
    order = {
        group_key: index
        for index, (group_key, _label) in enumerate(TRANSPORT_GROUPS)
    }
    return order.get(str(key), 99)


def _weather_rows(snapshot: dict[str, Any]) -> list[dict[str, Any]]:
    rows = [
        dict(row)
        for row in snapshot.get("weather", [])
        if isinstance(row, dict)
    ]
    runtime_zone_ids = {
        _as_int(row.get("zone"))
        for row in rows
        if _as_int(row.get("zone")) > 0
    }
    fallback_registry = canonical_weather_zone_registry(runtime_zone_ids)
    map_ids: set[int] = set()
    for row in rows:
        raw_map_id = row.get("map_id")
        zone_meta = fallback_registry.get(_as_int(row.get("zone")))
        if raw_map_id is not None:
            map_ids.add(_as_int(raw_map_id))
        elif zone_meta is not None:
            map_ids.add(int(zone_meta.map_id))
    map_names = map_name_lookup({map_id for map_id in map_ids if map_id >= 0})

    for row in rows:
        zone_id = _as_int(row.get("zone"))
        zone_meta = fallback_registry.get(zone_id)
        zone_name = str(
            row.get("canonical_name")
            or (zone_meta.name if zone_meta is not None else "")
            or f"Zone {zone_id}"
        )
        zone_name = _clean_zone_name(zone_name, zone_id)
        row["zone_name"] = zone_name
        if row.get("map_id") is not None:
            map_id = _as_int(row.get("map_id"))
        elif zone_meta is not None:
            map_id = int(zone_meta.map_id)
        else:
            map_id = -1
        row["map_id"] = map_id
        row["map_name"] = map_names.get(map_id, f"Map {map_id}") if map_id >= 0 else ""
        row["continent_name"] = _continent_name(map_id, row["map_name"])
        row["parent_zone"] = _as_int(row.get("parent_zone") or (zone_meta.parent_zone_id if zone_meta else 0))
        row["normalized_name"] = str(row.get("normalized_name") or (zone_meta.normalized_name if zone_meta else ""))
        aliases = row.get("search_aliases")
        if not isinstance(aliases, list):
            aliases = list(zone_meta.aliases) if zone_meta is not None else []
        row["search_aliases"] = [str(alias) for alias in aliases if str(alias or "").strip()]
        row["teleport_name"] = _teleport_name(zone_name)
        weather = _weather_state(
            _as_int(row.get("weather_type")),
            float(row.get("density", 0.0) or 0.0),
        )
        row["current"] = weather["label"]
        row["weather_family"] = weather["family"]
        row["weather_intensity"] = weather["intensity"]
        row["weather_icon"] = weather["icon"]
        row["weather_icon_key"] = weather["icon_key"]
        row["search_text"] = _weather_search_text(row)
        _sanitize_weather_runtime_row(row)
        row["weather_hash"] = _weather_hash(row)

    rows.sort(key=lambda item: str(item.get("zone_name", "")).lower())
    return rows


def _weather_state(weather_type: int, density: float) -> dict[str, str]:
    if int(weather_type) == 0 or float(density) <= 0.0:
        return {
            "family": "Clear",
            "intensity": "",
            "label": "Clear",
            "icon": WEATHER_ICONS["Clear"],
            "icon_key": "Clear",
        }

    family = "Rain"
    if int(weather_type) in (6, 7, 8, 106):
        family = "Snow"
    elif int(weather_type) in (1, 84, 85):
        family = "Fog"
    elif int(weather_type) in (22, 41, 42):
        family = "Unknown"
    elif int(weather_type) in (86, 90):
        family = "Storm"

    if float(density) >= 0.66:
        strength = "Heavy"
    elif float(density) >= 0.33:
        strength = "Medium"
    else:
        strength = "Light"

    if family in ("Unknown", "Fog", "Snow", "Storm"):
        label = family
    elif family == "Rain" and strength == "Heavy":
        label = "Heavy Rain"
    else:
        label = family
    icon_key = "Heavy Rain" if family == "Rain" and strength == "Heavy" else family
    return {
        "family": family,
        "intensity": strength,
        "label": label,
        "icon": WEATHER_ICONS.get(icon_key, WEATHER_ICONS["Unknown"]),
        "icon_key": icon_key if icon_key in WEATHER_ICONS else "Unknown",
    }


def _weather_hash(row: dict[str, Any]) -> str:
    values = (
        row.get("zone"),
        row.get("zone_name"),
        row.get("current"),
        row.get("weather_icon"),
        row.get("weather_icon_key"),
        row.get("map_id"),
        row.get("map_name"),
        row.get("continent_name"),
        row.get("search_text"),
    )
    return "|".join(str(value or "") for value in values)


def _transport_search_text(row: dict[str, Any]) -> str:
    category = str(row.get("category_label", "") or "")
    synonyms = {
        "Boats": "boat boats båt båtar",
        "Zeppelins": "zeppelin zeppelins zepelin zepelinare",
        "Elevators": "elevator elevators lift hiss hissar",
    }.get(category, "")
    return _normalized_search_text(
        row.get("name"),
        row.get("entry"),
        row.get("world_guid"),
        row.get("category"),
        category,
        synonyms,
        row.get("status_label"),
        row.get("location_name"),
        row.get("location_detail"),
        row.get("map_name"),
        row.get("meta_name"),
    )


def _transport_result_icon(category: str) -> str:
    if category == "zeppelins":
        return "☁"
    if category == "elevators":
        return "↕"
    return "⇄"


def _weather_search_text(row: dict[str, Any]) -> str:
    weather_terms = _weather_search_aliases(row)
    continent_terms = _continent_search_aliases(_as_int(row.get("map_id")), str(row.get("continent_name") or ""))
    return _normalized_search_text(
        row.get("zone_name"),
        row.get("zone"),
        row.get("map_name"),
        row.get("continent_name"),
        " ".join(continent_terms),
        row.get("normalized_name"),
        " ".join(row.get("search_aliases") or []),
        row.get("current"),
        row.get("weather_family"),
        row.get("weather_intensity"),
        row.get("weather_icon_key"),
        " ".join(weather_terms),
        "weather väder landskap kontinent",
    )


def _normalized_search_text(*values: Any) -> str:
    return " ".join(
        str(value or "").strip().lower()
        for value in values
        if str(value or "").strip()
    )


def _weather_search_aliases(row: dict[str, Any]) -> list[str]:
    family = str(row.get("weather_family") or "").strip().lower()
    label = str(row.get("current") or "").strip().lower()
    aliases = {
        "clear": ["clear", "sun", "sunny", "fine"],
        "rain": ["rain", "rainy", "raining"],
        "snow": ["snow", "snowy", "snowing"],
        "storm": ["storm", "storming", "thunder", "thunderstorm"],
        "fog": ["fog", "foggy"],
        "sand": ["sand", "sandstorm"],
    }.get(family, [])
    if "heavy rain" in label:
        aliases = [*aliases, "heavy rain", "downpour"]
    return aliases


def _continent_name(map_id: int, map_name: str) -> str:
    known = {
        0: "Eastern Kingdoms",
        1: "Kalimdor",
        530: "Outland",
        571: "Northrend",
        870: "Pandaria",
    }
    return known.get(int(map_id), str(map_name or "").strip())


def _continent_search_aliases(map_id: int, continent_name: str) -> list[str]:
    aliases = {
        0: ["eastern", "ek", "azeroth"],
        1: ["kalimdor"],
        530: ["outland", "outlands"],
        571: ["northrend", "northend"],
        870: ["pandaria"],
    }.get(int(map_id), [])
    name = str(continent_name or "").strip().lower()
    return [*aliases, name] if name else aliases


def _sanitize_weather_runtime_row(row: dict[str, Any]) -> None:
    allowed = {
        "zone",
        "parent_zone",
        "map_id",
        "map_name",
        "continent_name",
        "canonical_name",
        "zone_name",
        "normalized_name",
        "search_aliases",
        "teleport_name",
        "current",
        "weather_family",
        "weather_intensity",
        "weather_icon",
        "weather_icon_key",
        "search_text",
    }
    for key in list(row):
        if key not in allowed:
            row.pop(key, None)


def _teleport_name(zone_name: str) -> str:
    return str(zone_name or "").strip().replace('"', "").replace("'", "")


def _clean_zone_name(zone_name: str, zone_id: int) -> str:
    name = str(zone_name or "").strip()
    suffix = f" Zone {int(zone_id)}"
    if name.endswith(suffix):
        name = name[:-len(suffix)].strip()
    if not name or name == f"Zone {int(zone_id)}":
        return f"Zone {int(zone_id)}"
    return name


def _phase_percent(phase_ms: int, period_ms: int) -> int:
    if int(period_ms) <= 0:
        return 0
    return max(0, min(100, int(round((float(phase_ms) / float(period_ms)) * 100.0))))


def _format_generated_at(epoch_seconds: int) -> str:
    if int(epoch_seconds) <= 0:
        return "No runtime snapshot"
    return time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(int(epoch_seconds)))


def _format_generated_time(epoch_seconds: int) -> str:
    if int(epoch_seconds) <= 0:
        return "Never"
    return time.strftime("%H:%M:%S", time.localtime(int(epoch_seconds)))


def _as_int(value: Any) -> int:
    try:
        return int(value or 0)
    except (TypeError, ValueError):
        return 0
