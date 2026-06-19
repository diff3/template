#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from __future__ import annotations

from admin_panel.modules.config import DB_CONFIG
from admin_panel.modules.db import db_cursor, fetch_all, fetch_one, quote_identifier
from admin_panel.modules.metadata import enrich_character_rows


def table_columns(db_name: str) -> dict[str, set[str]]:
    rows = fetch_all(
        "characters",
        """
        SELECT TABLE_NAME, COLUMN_NAME
        FROM information_schema.COLUMNS
        WHERE TABLE_SCHEMA = %s
        """,
        (db_name,),
    )
    columns: dict[str, set[str]] = {}
    for row in rows:
        table = str(row["TABLE_NAME"])
        columns.setdefault(table, set()).add(str(row["COLUMN_NAME"]))
    return columns


def delete_account_characters(account_id: int) -> None:
    if account_id <= 0:
        raise ValueError("account_id must be positive")

    characters_db = DB_CONFIG["characters_db"]
    char_rows = fetch_all("characters", "SELECT guid FROM characters WHERE account = %s", (account_id,))
    guids = [int(row["guid"]) for row in char_rows]
    columns_by_table = table_columns(characters_db)

    # Character data is spread across many SkyFire tables. Delete by the
    # strongest owner key available, then remove the character rows last.
    with db_cursor("characters") as (_conn, cursor):
        for table in sorted(columns_by_table):
            if table == "characters":
                continue

            columns = columns_by_table[table]
            table_name = quote_identifier(table)
            if "account" in columns:
                cursor.execute(f"DELETE FROM {table_name} WHERE `account` = %s", (account_id,))
                continue
            if "owner_guid" in columns and guids:
                placeholders = ", ".join(["%s"] * len(guids))
                cursor.execute(f"DELETE FROM {table_name} WHERE `owner_guid` IN ({placeholders})", tuple(guids))
                continue
            if "guid" in columns and guids:
                placeholders = ", ".join(["%s"] * len(guids))
                cursor.execute(f"DELETE FROM {table_name} WHERE `guid` IN ({placeholders})", tuple(guids))

        cursor.execute("DELETE FROM `characters` WHERE `account` = %s", (account_id,))


def delete_character_data(guid: int) -> None:
    if guid <= 0:
        raise ValueError("guid must be positive")

    characters_db = DB_CONFIG["characters_db"]
    columns_by_table = table_columns(characters_db)

    # This is intentionally broad: sandbox character deletes should remove
    # dependent rows without maintaining a fragile hand-written table list.
    with db_cursor("characters") as (_conn, cursor):
        for table in sorted(columns_by_table):
            if table == "characters":
                continue

            columns = columns_by_table[table]
            table_name = quote_identifier(table)
            if "owner_guid" in columns:
                cursor.execute(f"DELETE FROM {table_name} WHERE `owner_guid` = %s", (guid,))
                continue
            if "guid" in columns:
                cursor.execute(f"DELETE FROM {table_name} WHERE `guid` = %s", (guid,))

        cursor.execute("DELETE FROM `characters` WHERE `guid` = %s", (guid,))


def account_characters(account_id: int) -> list[dict]:
    rows = fetch_all(
        "characters",
        """
        SELECT guid, name, race, gender, class AS class_id, level, map, zone, online
        FROM characters
        WHERE account = %s
        ORDER BY guid ASC
        """,
        (account_id,),
    )
    return enrich_character_rows(rows)


def character_rows() -> list[dict]:
    auth_db = quote_identifier(DB_CONFIG["auth_db"])
    rows = fetch_all(
        "characters",
        f"""
        SELECT
            c.guid,
            c.account,
            c.name,
            c.race,
            c.gender,
            c.class AS class_id,
            c.level,
            c.map,
            c.zone,
            c.online,
            a.username AS account_name
        FROM characters c
        LEFT JOIN {auth_db}.account a ON a.id = c.account
        ORDER BY c.name ASC
        """,
    )
    return enrich_character_rows(rows)


def online_character_rows() -> list[dict]:
    auth_db = quote_identifier(DB_CONFIG["auth_db"])
    rows = fetch_all(
        "characters",
        f"""
        SELECT
            c.guid,
            c.account,
            c.name,
            c.race,
            c.gender,
            c.class AS class_id,
            c.level,
            c.map,
            c.zone,
            a.username AS account_name
        FROM characters c
        LEFT JOIN {auth_db}.account a ON a.id = c.account
        WHERE c.online = 1
        ORDER BY c.name ASC
        """,
    )
    return enrich_character_rows(rows)


def get_account_character(account_id: int, guid: int) -> dict | None:
    return fetch_one(
        "characters",
        """
        SELECT guid, name
        FROM characters
        WHERE account = %s AND guid = %s
        """,
        (account_id, guid),
    )


def online_count() -> int:
    row = fetch_one("characters", "SELECT COUNT(*) AS count FROM characters WHERE online = 1")
    return int((row or {}).get("count") or 0)


def clear_online_flags() -> None:
    with db_cursor("characters") as (_conn, cursor):
        cursor.execute("UPDATE characters SET online = 0 WHERE online <> 0")


def character_count() -> int:
    row = fetch_one("characters", "SELECT COUNT(*) AS count FROM characters")
    return int((row or {}).get("count") or 0)
