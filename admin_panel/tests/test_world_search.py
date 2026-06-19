#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from __future__ import annotations

import sys
import types
from pathlib import Path

from server.modules.handlers.world.state.weather_zone_registry import WeatherZoneEntry

if "pymysql" not in sys.modules:
    pymysql_stub = types.ModuleType("pymysql")
    pymysql_stub.connect = lambda *args, **kwargs: None
    pymysql_stub.cursors = types.SimpleNamespace(DictCursor=object)
    sys.modules["pymysql"] = pymysql_stub

from admin_panel.modules import world_state


def _tokens(value: str) -> list[str]:
    return [part for part in str(value or "").lower().split() if part]


def _matching(results: list[dict], query: str) -> list[dict]:
    tokens = _tokens(query)
    return [
        row
        for row in results
        if all(token in str(row.get("search_text") or "").lower() for token in tokens)
    ]


def _weather_rows(monkeypatch):
    monkeypatch.setattr(
        world_state,
        "canonical_weather_zone_registry",
        lambda _explicit: {
            38: WeatherZoneEntry(
                38,
                0,
                0,
                "Loch Modan",
                "loch modan",
                ("The Loch",),
                (923,),
            ),
            148: WeatherZoneEntry(
                148,
                0,
                1,
                "Darkshore",
                "darkshore",
                ("Auberdine",),
                (465,),
            ),
        },
    )
    monkeypatch.setattr(
        world_state,
        "map_name_lookup",
        lambda _map_ids: {
            0: "Eastern Kingdoms",
            1: "Kalimdor",
        },
    )
    return world_state._weather_rows({
        "weather": [
            {"zone": 38, "weather_type": 0, "density": 0.0},
            {"zone": 148, "weather_type": 5, "density": 0.8},
        ],
    })


def _transport_rows():
    return [{
        "entry": 177233,
        "world_guid": 9001,
        "spawn_guid": 233,
        "map_id": 1,
        "map_name": "Kalimdor",
        "category": "boats",
        "category_label": "Boats",
        "name": "Ratchet ⇄ Booty Bay",
        "status_label": "Docked",
        "passenger_label": "2 passengers",
        "phase_label": "Phase 42%",
        "copy_command": ".go xyz 1 1.00 2.00 3.00 0.00",
        "search_text": "ratchet booty bay boat boats docked kalimdor",
    }]


def _clear_transport_metadata_caches():
    for func in (
        world_state._transport_metadata,
        world_state._taxi_path_route_names,
    ):
        if hasattr(func, "_cache"):
            delattr(func, "_cache")


def _runtime_transport_row(entry: int, *, spawn_guid: int = 1) -> dict:
    return {
        "entry": int(entry),
        "world_guid": 9000 + int(entry),
        "spawn_guid": int(spawn_guid),
        "map_id": 1,
        "phase_ms": 1000,
        "period_ms": 10000,
        "x": 1.0,
        "y": 2.0,
        "z": 3.0,
        "passenger_count": 0,
    }


def _render_single_transport(monkeypatch, runtime_row: dict, metadata_rows: list[dict]) -> dict:
    _clear_transport_metadata_caches()
    monkeypatch.setattr(world_state, "map_name_lookup", lambda _map_ids: {1: "Kalimdor"})
    monkeypatch.setattr(world_state, "fetch_all", lambda *_args, **_kwargs: list(metadata_rows))
    monkeypatch.setattr(world_state, "_taxi_path_route_names", lambda _path_ids: {})
    rows = world_state._transport_rows({"transports": [runtime_row]})
    assert len(rows) == 1
    return rows[0]


def test_transport_label_177233_uses_feathermoon_metadata(monkeypatch):
    row = _render_single_transport(
        monkeypatch,
        _runtime_transport_row(177233, spawn_guid=8),
        [{
            "guid": 8,
            "entry": 177233,
            "name": 'The Forgotten Coast, Feralas and Feathermoon Stronghold, Sardor Isle, Feralas ("Feathermoon Ferry")',
            "template_name": "Ship, Night Elf (Feathermoon Ferry)",
            "path_id": 777,
            "display_id": 7087,
        }],
    )

    assert row["name"] == "Feathermoon Ferry"
    assert row["label_source"] == "transports_table"
    assert row["path_id"] == 777


def test_transport_label_20808_uses_ratchet_booty_metadata(monkeypatch):
    row = _render_single_transport(
        monkeypatch,
        _runtime_transport_row(20808, spawn_guid=7),
        [{
            "guid": 7,
            "entry": 20808,
            "name": 'Steamwheedle Cartel ports, Ratchet and Booty Bay ("The Maiden\'s Fancy")',
            "template_name": "Ship (The Maiden's Fancy)",
            "path_id": 241,
            "display_id": 3015,
        }],
    )

    assert row["name"] == "Ratchet ⇄ Booty Bay"
    assert row["label_source"] == "transports_table"
    assert row["path_id"] == 241


def test_transport_metadata_beats_known_route_override(monkeypatch):
    row = _render_single_transport(
        monkeypatch,
        _runtime_transport_row(20808, spawn_guid=7),
        [{
            "guid": 7,
            "entry": 20808,
            "name": "Authoritative Test Ferry",
            "template_name": "Ignored Template Name",
            "path_id": 0,
            "display_id": 3015,
        }],
    )

    assert row["name"] == "Authoritative Test Ferry"
    assert row["label_source"] == "transports_table"


def test_transport_known_route_used_when_metadata_unavailable(monkeypatch):
    row = _render_single_transport(
        monkeypatch,
        _runtime_transport_row(20808, spawn_guid=7),
        [],
    )

    assert row["name"] == "Ratchet ⇄ Booty Bay"
    assert row["label_source"] == "known_override"


def test_transport_without_metadata_uses_fallback_label(monkeypatch):
    row = _render_single_transport(
        monkeypatch,
        _runtime_transport_row(999999, spawn_guid=999999),
        [],
    )

    assert row["name"] == "Transport 999999"
    assert row["label_source"] == "fallback"


def test_elevator_uses_gameobject_metadata_for_category_and_name(monkeypatch):
    row = _render_single_transport(
        monkeypatch,
        _runtime_transport_row(20649, spawn_guid=1234),
        [{
            "source": "gameobject",
            "guid": 1234,
            "entry": 20649,
            "name": None,
            "template_name": "Undervator",
            "path_id": 0,
            "display_id": 455,
            "object_type": 11,
            "map_id": 0,
            "x": 1595.0,
            "y": 240.0,
            "z": -40.0,
        }],
    )

    assert row["category"] == "elevators"
    assert row["name"] == "Undercity Elevator 1"
    assert row["label_source"] == "elevator"


def test_synced_elevator_phase_variants_are_collapsed(monkeypatch):
    _clear_transport_metadata_caches()
    monkeypatch.setattr(world_state, "map_name_lookup", lambda _map_ids: {1: "Kalimdor"})
    monkeypatch.setattr(world_state, "_taxi_path_route_names", lambda _path_ids: {})
    monkeypatch.setattr(
        world_state,
        "fetch_all",
        lambda *_args, **_kwargs: [
            {
                "source": "gameobject",
                "guid": 76,
                "entry": 206608,
                "name": None,
                "template_name": "Elevator",
                "path_id": 0,
                "display_id": 9542,
                "object_type": 11,
                "map_id": 1,
            },
            {
                "source": "gameobject",
                "guid": 100942,
                "entry": 219175,
                "name": None,
                "template_name": "Doodad_Orgrimmar_Elevator_01",
                "path_id": 0,
                "display_id": 9542,
                "object_type": 11,
                "map_id": 1136,
            },
        ],
    )

    rows = world_state._transport_rows({
        "transports": [
            {
                **_runtime_transport_row(206608, spawn_guid=76),
                "display_id": 9542,
                "x": 1704.78,
                "y": -4265.96,
                "z": 88.0,
            },
            {
                **_runtime_transport_row(219175, spawn_guid=100942),
                "display_id": 9542,
                "x": 1704.78,
                "y": -4265.96,
                "z": 88.0,
            },
        ],
    })

    assert len(rows) == 1
    assert rows[0]["entry"] == 206608
    assert rows[0]["name"] == "Orgrimmar Elevator 1"
    assert rows[0]["synced_variant_count"] == 2


def test_loch_returns_weather_and_zone_results(monkeypatch):
    results = world_state._world_search_results(_transport_rows(), _weather_rows(monkeypatch))
    matches = _matching(results, "loch")
    types = {row["type"] for row in matches}

    assert "weather" in types
    assert "zone" in types
    assert any(row["title"] == "Loch Modan" for row in matches)


def test_transport_results_survive_weather_search_refactor(monkeypatch):
    results = world_state._world_search_results(_transport_rows(), _weather_rows(monkeypatch))
    matches = _matching(results, "ratchet")

    assert any(row["type"] == "transport" for row in matches)
    assert any(row["title"] == "Ratchet ⇄ Booty Bay" for row in matches)


def test_mixed_search_preserves_multiple_result_types(monkeypatch):
    monkeypatch.setattr(
        world_state,
        "_teleport_rows_for_search",
        lambda: [{"name": "Ratchet", "map": 1, "map_name": "Kalimdor"}],
    )
    results = world_state._world_search_results(_transport_rows(), _weather_rows(monkeypatch))
    matches = _matching(results, "ratchet")
    types = {row["type"] for row in matches}

    assert {"transport", "teleport"}.issubset(types)


def test_no_result_category_silently_disappears(monkeypatch):
    monkeypatch.setattr(
        world_state,
        "_teleport_rows_for_search",
        lambda: [{"name": "Loch Modan", "map": 0, "map_name": "Eastern Kingdoms"}],
    )
    monkeypatch.setattr(
        world_state,
        "_command_rows_for_search",
        lambda: [{
            "name": "tele",
            "usage": ".tele <name>",
            "aliases": ["tel"],
            "allow_args": True,
            "require_args": True,
        }],
    )
    results = world_state._world_search_results(_transport_rows(), _weather_rows(monkeypatch))
    types = {row["type"] for row in results}

    assert {"weather", "transport", "teleport", "zone", "continent", "command"}.issubset(types)


def test_renderer_handles_transport_weather_and_teleport_result_types():
    template = Path("admin_panel/templates/world.html").read_text(encoding="utf-8")

    assert "function renderSearchResult(result)" in template
    assert "transport:" in template
    assert "weather:" in template
    assert "teleport:" in template
    assert "data-copy-search-result" in template
