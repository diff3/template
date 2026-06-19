#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from __future__ import annotations

from server.modules.handlers.world.commands.chat_commands import ALIASES, PRIMARY_COMMANDS


def command_rows() -> list[dict]:
    alias_lookup: dict[str, list[str]] = {}
    for alias, command_name in ALIASES.items():
        alias_lookup.setdefault(command_name, []).append(alias)

    rows = []
    for name, command in sorted(PRIMARY_COMMANDS.items()):
        rows.append(
            {
                "name": name,
                "usage": command.usage,
                "aliases": sorted(alias_lookup.get(name, [])),
                "allow_args": bool(command.allow_args),
                "require_args": bool(command.require_args),
            }
        )
    return rows


def command_count() -> int:
    return len(PRIMARY_COMMANDS)
