#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from __future__ import annotations

from contextlib import contextmanager

import pymysql

from admin_panel.modules.config import DB_CONFIG


def db_name(kind: str) -> str:
    if kind == "auth":
        return DB_CONFIG["auth_db"]
    if kind == "characters":
        return DB_CONFIG["characters_db"]
    if kind == "world":
        return DB_CONFIG["world_db"]
    raise ValueError(f"Unknown db kind: {kind}")


def connect(kind: str):
    # Keep DB waits bounded. Admin actions should fail visibly, not hang.
    return pymysql.connect(
        host=DB_CONFIG["host"],
        port=int(DB_CONFIG.get("port", 3306)),
        user=DB_CONFIG["username"],
        password=DB_CONFIG["password"],
        database=db_name(kind),
        charset="utf8mb4",
        cursorclass=pymysql.cursors.DictCursor,
        autocommit=False,
        connect_timeout=1,
        read_timeout=2,
        write_timeout=2,
    )


@contextmanager
def db_cursor(kind: str):
    conn = connect(kind)
    try:
        with conn.cursor() as cursor:
            yield conn, cursor
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def fetch_all(kind: str, sql: str, params: tuple | dict | None = None) -> list[dict]:
    with db_cursor(kind) as (_conn, cursor):
        cursor.execute(sql, params or ())
        return list(cursor.fetchall())


def fetch_one(kind: str, sql: str, params: tuple | dict | None = None) -> dict | None:
    rows = fetch_all(kind, sql, params)
    return rows[0] if rows else None


def quote_identifier(value: str) -> str:
    return "`" + value.replace("`", "``") + "`"
