#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from __future__ import annotations

import time

from admin_panel.modules.config import GM_LEVELS
from admin_panel.modules.db import db_cursor, fetch_all, fetch_one


def account_summary_rows() -> list[dict]:
    return fetch_all(
        "auth",
        """
        SELECT
            a.id,
            a.username,
            a.email,
            a.expansion,
            COALESCE(MAX(aa.gmlevel), 0) AS gmlevel,
            EXISTS (
                SELECT 1
                FROM account_banned b
                WHERE b.id = a.id AND b.active = 1
            ) AS banned
        FROM account a
        LEFT JOIN account_access aa ON aa.id = a.id
        GROUP BY a.id, a.username, a.email, a.expansion
        ORDER BY a.id DESC
        """,
    )


def account_count() -> int:
    row = fetch_one("auth", "SELECT COUNT(*) AS count FROM account")
    return int((row or {}).get("count") or 0)


def get_account(account_id: int) -> dict | None:
    return fetch_one("auth", "SELECT * FROM account WHERE id = %s", (account_id,))


def get_account_gmlevel(account_id: int) -> int:
    row = fetch_one(
        "auth",
        "SELECT COALESCE(MAX(gmlevel), 0) AS gmlevel FROM account_access WHERE id = %s",
        (account_id,),
    )
    return int((row or {}).get("gmlevel") or 0)


def set_account_gmlevel(account_id: int, gmlevel: int) -> None:
    gmlevel = max(0, min(int(gmlevel), max(GM_LEVELS)))
    with db_cursor("auth") as (_conn, cursor):
        # Keep one global GM row. Realm-specific access is outside this panel.
        cursor.execute("DELETE FROM account_access WHERE id = %s", (account_id,))
        if gmlevel > 0:
            cursor.execute(
                """
                INSERT INTO account_access (id, gmlevel, RealmID)
                VALUES (%s, %s, %s)
                """,
                (account_id, gmlevel, -1),
            )


def is_account_banned(account_id: int) -> bool:
    row = fetch_one(
        "auth",
        "SELECT COUNT(*) AS count FROM account_banned WHERE id = %s AND active = 1",
        (account_id,),
    )
    return bool(int((row or {}).get("count") or 0))


def next_ban_timestamp(account_id: int) -> int:
    timestamp = int(time.time())
    row = fetch_one(
        "auth",
        "SELECT MAX(bandate) AS latest FROM account_banned WHERE id = %s",
        (account_id,),
    )
    latest = int((row or {}).get("latest") or 0)
    if timestamp <= latest:
        return latest + 1
    return timestamp


def set_account_banned(account_id: int, banned: bool, banned_by: str) -> None:
    now = next_ban_timestamp(account_id)
    if banned:
        with db_cursor("auth") as (_conn, cursor):
            cursor.execute(
                """
                UPDATE account_banned
                SET active = 0
                WHERE id = %s AND active = 1
                """,
                (account_id,),
            )
            cursor.execute(
                """
                INSERT INTO account_banned (id, bandate, unbandate, bannedby, banreason, active)
                VALUES (%s, %s, %s, %s, %s, %s)
                """,
                (account_id, now, 0, banned_by or "WEB", "Banned from admin panel", 1),
            )
        return

    with db_cursor("auth") as (_conn, cursor):
        cursor.execute(
            """
            UPDATE account_banned
            SET active = 0, unbandate = %s
            WHERE id = %s AND active = 1
            """,
            (now, account_id),
        )


def insert_account(username: str, password_data: tuple[bytes, bytes], email: str, expansion: int) -> int:
    salt, verifier = password_data
    with db_cursor("auth") as (_conn, cursor):
        cursor.execute(
            """
            INSERT INTO account
                (username, salt, verifier, session_key, token_key, email, reg_mail, last_ip, locked, expansion, os)
            VALUES
                (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """,
            (username, salt, verifier, b"", b"", email, email, "0.0.0.0", 0, expansion, "Win"),
        )
        return int(cursor.lastrowid)


def update_account(
    account_id: int,
    username: str,
    email: str,
    expansion: int,
    password_data: tuple[bytes, bytes] | None,
) -> None:
    with db_cursor("auth") as (_conn, cursor):
        if password_data is not None:
            salt, verifier = password_data
            cursor.execute(
                """
                UPDATE account
                SET username = %s, email = %s, reg_mail = %s, expansion = %s, salt = %s, verifier = %s
                WHERE id = %s
                """,
                (username, email, email, expansion, salt, verifier, account_id),
            )
            return

        cursor.execute(
            """
            UPDATE account
            SET username = %s, email = %s, reg_mail = %s, expansion = %s
            WHERE id = %s
            """,
            (username, email, email, expansion, account_id),
        )


def delete_account_auth_rows(account_id: int) -> None:
    with db_cursor("auth") as (_conn, cursor):
        cursor.execute("DELETE FROM account_access WHERE id = %s", (account_id,))
        cursor.execute("DELETE FROM account_banned WHERE id = %s", (account_id,))
        cursor.execute("DELETE FROM account WHERE id = %s", (account_id,))
