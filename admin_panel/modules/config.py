#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from __future__ import annotations

import os
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from shared.ConfigLoader import ConfigLoader

CONFIG = ConfigLoader.get_config()
DB_CONFIG = CONFIG["database"]
DEFAULT_CONFIG_PATH = PROJECT_ROOT / "config" / "default.yaml"
PROXY_CONFIG_PATH = PROJECT_ROOT / "config" / "proxy.json"
RUNNING_IN_DOCKER = Path("/.dockerenv").exists()
FLASK_SECRET = os.environ.get(
    "FLASK_ADMIN_SECRET",
    f"{CONFIG.get('project_name', 'PyPandariaEmu')}-admin-secret",
)

REALM_TYPES = {
    0: "Normal",
    1: "PvP",
    4: "RP",
    6: "RP PvP",
}

EXPANSIONS = {
    0: "Classic",
    1: "The Burning Crusade",
    2: "Wrath of the Lich King",
    3: "Cataclysm",
    4: "Mists of Pandaria",
}

EXPANSION_SHORT_NAMES = {
    0: "Classic",
    1: "TBC",
    2: "WotLK",
    3: "Cata",
    4: "MoP",
}

GM_LEVELS = {
    0: "Player",
    1: "Moderator",
    2: "Game Master",
    3: "Administrator",
}

RACE_NAMES = {
    1: "Human",
    2: "Orc",
    3: "Dwarf",
    4: "Night Elf",
    5: "Undead",
    6: "Tauren",
    7: "Gnome",
    8: "Troll",
    9: "Goblin",
    10: "Blood Elf",
    11: "Draenei",
    22: "Worgen",
    24: "Pandaren",
    25: "Pandaren Alliance",
    26: "Pandaren Horde",
}

CLASS_NAMES = {
    1: "Warrior",
    2: "Paladin",
    3: "Hunter",
    4: "Rogue",
    5: "Priest",
    6: "Death Knight",
    7: "Shaman",
    8: "Mage",
    9: "Warlock",
    10: "Monk",
    11: "Druid",
}

MAP_NAMES = {
    0: "Eastern Kingdoms",
    1: "Kalimdor",
    530: "Outland",
    571: "Northrend",
    609: "The Ruby Sanctum",
    646: "Deepholm",
    648: "Lost Isles",
    654: "Gilneas",
    730: "Maelstrom",
    860: "The Wandering Isle",
    870: "Pandaria",
}
