#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from __future__ import annotations

import os
import sys
from contextlib import contextmanager
from functools import wraps
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import pymysql
from flask import Flask, flash, redirect, render_template, request, session, url_for

from server.modules.crypto.SRP6Crypto import SRP6Crypto
from shared.ConfigLoader import ConfigLoader


CONFIG = ConfigLoader.get_config()
DB_CONFIG = CONFIG["database"]

app = Flask(__name__)
app.secret_key = os.environ.get(
    "FLASK_ADMIN_SECRET",
    f"{CONFIG.get('project_name', 'PyPandariaEmu')}-admin-secret",
)


def _db_name(kind: str) -> str:
    if kind == "auth":
        return DB_CONFIG["auth_db"]
    if kind == "characters":
        return DB_CONFIG["characters_db"]
    if kind == "world":
        return DB_CONFIG["world_db"]
    raise ValueError(f"Unknown db kind: {kind}")


def _connect(kind: str):
    return pymysql.connect(
        host=DB_CONFIG["host"],
        port=int(DB_CONFIG.get("port", 3306)),
        user=DB_CONFIG["username"],
        password=DB_CONFIG["password"],
        database=_db_name(kind),
        charset="utf8mb4",
        cursorclass=pymysql.cursors.DictCursor,
        autocommit=False,
    )


@contextmanager
def db_cursor(kind: str):
    conn = _connect(kind)
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


def require_login(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        if not session.get("account_id"):
            return redirect(url_for("login", next=request.path))
        return view(*args, **kwargs)

    return wrapped


def as_int(name: str, default: int = 0) -> int:
    value = (request.form.get(name) or "").strip()
    if value == "":
        return default
    return int(value)


def as_float(name: str, default: float = 0.0) -> float:
    value = (request.form.get(name) or "").strip()
    if value == "":
        return default
    return float(value)


def as_text(name: str, default: str = "") -> str:
    return (request.form.get(name) or default).strip()


def is_checked(name: str) -> int:
    return 1 if request.form.get(name) else 0


def make_srp6_credentials(username: str, password: str) -> tuple[bytes, bytes]:
    core = SRP6Crypto(mode=CONFIG.get("crypto", {}).get("srp6_mode", "skyfire"))
    salt = core.generate_salt()
    verifier = core.calculate_verifier(username, password, salt)
    return salt, verifier


def verify_admin_login(username: str, password: str) -> dict | None:
    account = fetch_one(
        "auth",
        """
        SELECT a.id, a.username, a.salt, a.verifier, COALESCE(MAX(aa.gmlevel), 0) AS gmlevel
        FROM account a
        LEFT JOIN account_access aa ON aa.id = a.id
        WHERE a.username = %s
        GROUP BY a.id, a.username, a.salt, a.verifier
        """,
        (username.upper(),),
    )
    if not account:
        return None

    gmlevel = int(account.get("gmlevel") or 0)
    if gmlevel <= 0:
        return None

    salt = bytes(account.get("salt") or b"")
    verifier = bytes(account.get("verifier") or b"")
    if not salt or not verifier:
        return None

    core = SRP6Crypto(mode=CONFIG.get("crypto", {}).get("srp6_mode", "skyfire"))
    if not core.check_password(account["username"], password, salt, verifier):
        return None
    return account


def safe_next_url(value: str | None) -> str:
    if value and value.startswith("/") and not value.startswith("//"):
        return value
    return url_for("index")


def account_summary_rows() -> list[dict]:
    return fetch_all(
        "auth",
        """
        SELECT
            a.id,
            a.username,
            a.email,
            a.expansion,
            a.locked,
            a.last_ip,
            a.os,
            COALESCE(MAX(aa.gmlevel), 0) AS gmlevel,
            GROUP_CONCAT(CONCAT(aa.RealmID, ':', aa.gmlevel) ORDER BY aa.RealmID SEPARATOR ', ') AS access_rows,
            latest_ban.active AS banned_active,
            latest_ban.bandate,
            latest_ban.unbandate,
            latest_ban.banreason
        FROM account a
        LEFT JOIN account_access aa ON aa.id = a.id
        LEFT JOIN (
            SELECT b1.*
            FROM account_banned b1
            INNER JOIN (
                SELECT id, MAX(bandate) AS latest_bandate
                FROM account_banned
                GROUP BY id
            ) b2
                ON b2.id = b1.id AND b2.latest_bandate = b1.bandate
        ) latest_ban ON latest_ban.id = a.id
        GROUP BY
            a.id, a.username, a.email, a.expansion, a.locked, a.last_ip, a.os,
            latest_ban.active, latest_ban.bandate, latest_ban.unbandate, latest_ban.banreason
        ORDER BY a.id DESC
        """,
    )


def get_account(account_id: int) -> dict | None:
    return fetch_one("auth", "SELECT * FROM account WHERE id = %s", (account_id,))


def get_account_access_rows(account_id: int) -> list[dict]:
    return fetch_all(
        "auth",
        "SELECT id, gmlevel, RealmID FROM account_access WHERE id = %s ORDER BY RealmID ASC",
        (account_id,),
    )


def get_account_bans(account_id: int) -> list[dict]:
    return fetch_all(
        "auth",
        """
        SELECT id, bandate, unbandate, bannedby, banreason, active
        FROM account_banned
        WHERE id = %s
        ORDER BY bandate DESC
        """,
        (account_id,),
    )


def realm_rows() -> list[dict]:
    return fetch_all(
        "auth",
        """
        SELECT id, name, address, port, icon, flag, timezone, allowedSecurityLevel
        FROM realmlist
        ORDER BY id ASC
        """,
    )


def character_rows() -> list[dict]:
    return fetch_all(
        "characters",
        """
        SELECT
            guid,
            realm,
            account,
            name,
            race,
            class AS class_id,
            level,
            money,
            map,
            position_x,
            position_y,
            position_z,
            orientation,
            health,
            power1
        FROM characters
        ORDER BY guid DESC
        LIMIT 500
        """,
    )


def get_character(guid: int) -> dict | None:
    return fetch_one(
        "characters",
        """
        SELECT
            guid,
            realm,
            account,
            name,
            race,
            class AS class_id,
            level,
            money,
            map,
            position_x,
            position_y,
            position_z,
            orientation,
            health,
            power1
        FROM characters
        WHERE guid = %s
        """,
        (guid,),
    )


def get_realm(realm_id: int) -> dict | None:
    return fetch_one("auth", "SELECT * FROM realmlist WHERE id = %s", (realm_id,))


@app.route("/")
@require_login
def index():
    counts = {
        "accounts": fetch_one("auth", "SELECT COUNT(*) AS count FROM account")["count"],
        "characters": fetch_one("characters", "SELECT COUNT(*) AS count FROM characters")["count"],
        "realms": fetch_one("auth", "SELECT COUNT(*) AS count FROM realmlist")["count"],
    }
    return render_template("index.html", counts=counts)


@app.route("/login", methods=["GET", "POST"])
def login():
    if session.get("account_id"):
        return redirect(url_for("index"))

    error = None
    if request.method == "POST":
        username = as_text("username").upper()
        password = request.form.get("password") or ""
        account = verify_admin_login(username, password)
        if account:
            session.clear()
            session["account_id"] = int(account["id"])
            session["username"] = account["username"]
            session["gmlevel"] = int(account["gmlevel"] or 0)
            flash("Logged in.", "success")
            next_url = safe_next_url(request.args.get("next"))
            return redirect(next_url)
        error = "Invalid credentials or missing gmlevel."

    return render_template("login.html", error=error)


@app.route("/logout", methods=["POST"])
@require_login
def logout():
    session.clear()
    flash("Logged out.", "success")
    return redirect(url_for("login"))


@app.route("/accounts")
@require_login
def accounts():
    return render_template("accounts/list.html", accounts=account_summary_rows())


@app.route("/accounts/new", methods=["GET", "POST"])
@require_login
def account_create():
    if request.method == "POST":
        username = as_text("username").upper()
        password = request.form.get("password") or ""
        email = as_text("email")
        expansion = as_int("expansion", 5)
        locked = is_checked("locked")
        last_ip = as_text("last_ip", "0.0.0.0") or "0.0.0.0"
        os_name = as_text("os", "Win") or "Win"

        if not username or not password:
            flash("Username and password are required.", "error")
            return render_template("accounts/form.html", account=None, access_rows=[], bans=[], realms=realm_rows())

        salt, verifier = make_srp6_credentials(username, password)

        with db_cursor("auth") as (conn, cursor):
            cursor.execute(
                """
                INSERT INTO account
                    (username, salt, verifier, session_key, token_key, email, reg_mail, last_ip, locked, expansion, os)
                VALUES
                    (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                """,
                (username, salt, verifier, b"", b"", email, email, last_ip, locked, expansion, os_name),
            )
            account_id = int(cursor.lastrowid)

            gmlevel = request.form.get("gmlevel")
            realm_id = request.form.get("realmID")
            if (gmlevel or "").strip() != "" and (realm_id or "").strip() != "":
                cursor.execute(
                    """
                    INSERT INTO account_access (id, gmlevel, RealmID)
                    VALUES (%s, %s, %s)
                    """,
                    (account_id, int(gmlevel), int(realm_id)),
                )

        flash("Account created.", "success")
        return redirect(url_for("account_edit", account_id=account_id))

    return render_template("accounts/form.html", account=None, access_rows=[], bans=[], realms=realm_rows())


@app.route("/accounts/<int:account_id>/edit", methods=["GET", "POST"])
@require_login
def account_edit(account_id: int):
    account = get_account(account_id)
    if not account:
        flash("Account not found.", "error")
        return redirect(url_for("accounts"))

    if request.method == "POST":
        username = as_text("username").upper()
        email = as_text("email")
        expansion = as_int("expansion", int(account.get("expansion") or 5))
        locked = is_checked("locked")
        last_ip = as_text("last_ip", account.get("last_ip") or "0.0.0.0")
        os_name = as_text("os", account.get("os") or "Win")
        password = request.form.get("password") or ""

        with db_cursor("auth") as (_conn, cursor):
            if password:
                salt, verifier = make_srp6_credentials(username, password)
                cursor.execute(
                    """
                    UPDATE account
                    SET username = %s, email = %s, reg_mail = %s, expansion = %s,
                        locked = %s, last_ip = %s, os = %s, salt = %s, verifier = %s
                    WHERE id = %s
                    """,
                    (username, email, email, expansion, locked, last_ip, os_name, salt, verifier, account_id),
                )
            else:
                cursor.execute(
                    """
                    UPDATE account
                    SET username = %s, email = %s, reg_mail = %s, expansion = %s,
                        locked = %s, last_ip = %s, os = %s
                    WHERE id = %s
                    """,
                    (username, email, email, expansion, locked, last_ip, os_name, account_id),
                )

        flash("Account updated.", "success")
        return redirect(url_for("account_edit", account_id=account_id))

    return render_template(
        "accounts/form.html",
        account=account,
        access_rows=get_account_access_rows(account_id),
        bans=get_account_bans(account_id),
        realms=realm_rows(),
    )


@app.post("/accounts/<int:account_id>/delete")
@require_login
def account_delete(account_id: int):
    with db_cursor("auth") as (_auth_conn, auth_cursor):
        auth_cursor.execute("DELETE FROM account_access WHERE id = %s", (account_id,))
        auth_cursor.execute("DELETE FROM account_banned WHERE id = %s", (account_id,))
        auth_cursor.execute("DELETE FROM account WHERE id = %s", (account_id,))
    with db_cursor("characters") as (_char_conn, char_cursor):
        char_cursor.execute("DELETE FROM characters WHERE account = %s", (account_id,))
    flash("Account deleted.", "success")
    return redirect(url_for("accounts"))


@app.post("/accounts/<int:account_id>/access")
@require_login
def account_access_save(account_id: int):
    realm_id = as_int("realmID", -1)
    gmlevel = as_int("gmlevel", 0)
    with db_cursor("auth") as (_conn, cursor):
        cursor.execute(
            """
            INSERT INTO account_access (id, gmlevel, RealmID)
            VALUES (%s, %s, %s)
            ON DUPLICATE KEY UPDATE gmlevel = VALUES(gmlevel)
            """,
            (account_id, gmlevel, realm_id),
        )
    flash("Account access saved.", "success")
    return redirect(url_for("account_edit", account_id=account_id))


@app.post("/accounts/<int:account_id>/access/<int:realm_id>/delete")
@require_login
def account_access_delete(account_id: int, realm_id: int):
    with db_cursor("auth") as (_conn, cursor):
        cursor.execute(
            "DELETE FROM account_access WHERE id = %s AND RealmID = %s",
            (account_id, realm_id),
        )
    flash("Account access deleted.", "success")
    return redirect(url_for("account_edit", account_id=account_id))


@app.post("/accounts/<int:account_id>/bans")
@require_login
def account_ban_create(account_id: int):
    bandate = as_int("bandate", 0)
    unbandate = as_int("unbandate", 0)
    reason = as_text("banreason")
    banned_by = as_text("bannedby", session.get("username", "WEB"))
    active = is_checked("active")

    with db_cursor("auth") as (_conn, cursor):
        cursor.execute(
            """
            INSERT INTO account_banned (id, bandate, unbandate, bannedby, banreason, active)
            VALUES (%s, %s, %s, %s, %s, %s)
            """,
            (account_id, bandate, unbandate, banned_by, reason, active),
        )
    flash("Ban entry created.", "success")
    return redirect(url_for("account_edit", account_id=account_id))


@app.post("/accounts/<int:account_id>/bans/<int:bandate>/delete")
@require_login
def account_ban_delete(account_id: int, bandate: int):
    with db_cursor("auth") as (_conn, cursor):
        cursor.execute(
            "DELETE FROM account_banned WHERE id = %s AND bandate = %s",
            (account_id, bandate),
        )
    flash("Ban entry deleted.", "success")
    return redirect(url_for("account_edit", account_id=account_id))


@app.route("/characters")
@require_login
def characters():
    return render_template("characters/list.html", characters=character_rows())


@app.route("/characters/<int:guid>/edit", methods=["GET", "POST"])
@require_login
def character_edit(guid: int):
    character = get_character(guid)
    if not character:
        flash("Character not found.", "error")
        return redirect(url_for("characters"))

    if request.method == "POST":
        with db_cursor("characters") as (_conn, cursor):
            cursor.execute(
                """
                UPDATE characters
                SET
                    name = %s,
                    race = %s,
                    class = %s,
                    level = %s,
                    money = %s,
                    map = %s,
                    position_x = %s,
                    position_y = %s,
                    position_z = %s,
                    health = %s,
                    power1 = %s,
                    account = %s
                WHERE guid = %s
                """,
                (
                    as_text("name"),
                    as_int("race"),
                    as_int("class_id"),
                    as_int("level"),
                    as_int("money"),
                    as_int("map"),
                    as_float("position_x"),
                    as_float("position_y"),
                    as_float("position_z"),
                    as_int("health"),
                    as_int("power1"),
                    as_int("account"),
                    guid,
                ),
            )
        flash("Character updated.", "success")
        return redirect(url_for("character_edit", guid=guid))

    return render_template("characters/form.html", character=character)


@app.post("/characters/<int:guid>/delete")
@require_login
def character_delete(guid: int):
    with db_cursor("characters") as (_conn, cursor):
        cursor.execute("DELETE FROM characters WHERE guid = %s", (guid,))
    flash("Character deleted.", "success")
    return redirect(url_for("characters"))


@app.route("/realmlist")
@require_login
def realmlist():
    return render_template("realmlist/list.html", realms=realm_rows())


@app.route("/realmlist/new", methods=["GET", "POST"])
@require_login
def realm_create():
    if request.method == "POST":
        with db_cursor("auth") as (_conn, cursor):
            cursor.execute(
                """
                INSERT INTO realmlist
                    (id, name, address, port, icon, flag, timezone, allowedSecurityLevel)
                VALUES
                    (%s, %s, %s, %s, %s, %s, %s, %s)
                """,
                (
                    as_int("id"),
                    as_text("name"),
                    as_text("address"),
                    as_int("port", 8085),
                    as_int("icon", 1),
                    as_int("flag", 0),
                    as_int("timezone", 1),
                    as_int("allowedSecurityLevel", 0),
                ),
            )
        flash("Realm created.", "success")
        return redirect(url_for("realmlist"))

    return render_template("realmlist/form.html", realm=None)


@app.route("/realmlist/<int:realm_id>/edit", methods=["GET", "POST"])
@require_login
def realm_edit(realm_id: int):
    realm = get_realm(realm_id)
    if not realm:
        flash("Realm not found.", "error")
        return redirect(url_for("realmlist"))

    if request.method == "POST":
        with db_cursor("auth") as (_conn, cursor):
            cursor.execute(
                """
                UPDATE realmlist
                SET
                    name = %s,
                    address = %s,
                    port = %s,
                    icon = %s,
                    flag = %s,
                    timezone = %s,
                    allowedSecurityLevel = %s
                WHERE id = %s
                """,
                (
                    as_text("name"),
                    as_text("address"),
                    as_int("port", 8085),
                    as_int("icon", 1),
                    as_int("flag", 0),
                    as_int("timezone", 1),
                    as_int("allowedSecurityLevel", 0),
                    realm_id,
                ),
            )
        flash("Realm updated.", "success")
        return redirect(url_for("realm_edit", realm_id=realm_id))

    return render_template("realmlist/form.html", realm=realm)


@app.post("/realmlist/<int:realm_id>/delete")
@require_login
def realm_delete(realm_id: int):
    with db_cursor("auth") as (_conn, cursor):
        cursor.execute("DELETE FROM realmlist WHERE id = %s", (realm_id,))
    flash("Realm deleted.", "success")
    return redirect(url_for("realmlist"))


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5001, debug=True)
