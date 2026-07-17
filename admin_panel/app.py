#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from __future__ import annotations

import sys
from functools import wraps
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from flask import (
    Flask,
    flash,
    jsonify,
    redirect,
    render_template,
    request,
    session,
    url_for,
)

from admin_panel.modules.accounts import (
    account_count,
    account_summary_rows,
    delete_account_auth_rows,
    get_account,
    get_account_gmlevel,
    insert_account,
    is_account_banned,
    set_account_banned,
    set_account_gmlevel,
    update_account,
)
from admin_panel.modules.auth import make_srp6_credentials, verify_admin_login
from admin_panel.modules.characters import (
    account_characters,
    character_count,
    character_rows,
    delete_account_characters,
    delete_character_data,
    get_account_character,
    online_character_rows,
)
from admin_panel.modules.commands import command_count, command_rows
from admin_panel.modules.config import EXPANSION_SHORT_NAMES, EXPANSIONS, FLASK_SECRET, GM_LEVELS, REALM_TYPES
from admin_panel.modules.db import db_cursor
from admin_panel.modules.forms import as_int, as_text, is_checked
from admin_panel.modules.lookup import LOOKUP_KINDS, lookup_rows, normalize_lookup_kind
from admin_panel.modules.metadata import faction_counts
from admin_panel.modules.realms import (
    delete_realm,
    get_motd,
    get_realm,
    insert_realm,
    realm_count,
    realm_rows,
    save_motd,
    update_realm,
)
from admin_panel.modules.status import server_status
from admin_panel.modules.teleports import (
    delete_teleport,
    get_teleport,
    load_teleport_cache,
    save_teleport,
    teleport_count,
    teleport_rows,
    warm_teleport_cache,
)
from admin_panel.modules.world_state import (
    world_dashboard,
)
from admin_panel.modules.world_api import (
    WorldAPIError,
    send_system_mail,
    send_whisper,
    send_world_chat,
)


app = Flask(__name__)
app.secret_key = FLASK_SECRET


def require_login(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        if not session.get("account_id"):
            return redirect(url_for("login", next=request.path))
        return view(*args, **kwargs)

    return wrapped


def safe_next_url(value: str | None) -> str:
    if value and value.startswith("/") and not value.startswith("//"):
        return value
    return url_for("index")


@app.route("/")
@require_login
def index():
    status = server_status()
    online_characters = online_character_rows() if status["worldserver"] else []
    counts = {
        "accounts": account_count(),
        "characters": character_count(),
        "online": len(online_characters),
        "realms": realm_count(),
        "commands": command_count(),
        "teleports": teleport_count(),
    }
    return render_template(
        "index.html",
        counts=counts,
        online_characters=online_characters,
        online_factions=faction_counts(online_characters),
    )


@app.route("/world")
@require_login
def world():
    return render_template("world.html", dashboard=world_dashboard())


@app.route("/world/runtime.json")
@require_login
def world_runtime_json():
    return jsonify(world_dashboard())


@app.route("/commands")
@require_login
def commands_help():
    return render_template("commands.html", commands=command_rows())


@app.route("/messages", methods=["GET", "POST"])
@require_login
def messages():
    if request.method == "POST":
        action = as_text("action")
        try:
            if action == "chat":
                chat_type = as_text("chat_type") or "world"
                target = as_text("target")
                message = as_text("message")
                if not message:
                    raise ValueError("Message is required.")
                author = str(session.get("username") or "Admin")
                if chat_type == "whisper":
                    if not target:
                        raise ValueError("Player name is required for a whisper.")
                    send_whisper(target, message, author)
                    flash(f"Whisper queued for {target}.", "success")
                elif chat_type == "world":
                    send_world_chat(message, author)
                    flash("World message queued.", "success")
                else:
                    raise ValueError("Invalid chat type.")
            elif action == "mail":
                recipient = as_text("recipient")
                subject = as_text("subject")
                body = as_text("body")
                if not recipient or not subject or not body:
                    raise ValueError("Recipient, subject and body are required.")
                result = send_system_mail(recipient, subject, body)
                flash(f"Mail sent to {recipient} (ID {int(result['mail_id'])}).", "success")
            else:
                raise ValueError("Invalid message action.")
        except (ValueError, WorldAPIError, KeyError, TypeError) as exc:
            flash(str(exc), "error")
        return redirect(url_for("messages"))

    return render_template("messages.html")


@app.route("/lookup")
@require_login
def lookup():
    kind = normalize_lookup_kind(request.args.get("kind"))
    query = str(request.args.get("q") or "").strip()
    return render_template(
        "lookup.html",
        kind=kind,
        kinds=LOOKUP_KINDS,
        query=query,
        rows=lookup_rows(kind, query),
    )


@app.route("/login", methods=["GET", "POST"])
def login():
    if session.get("account_id"):
        return redirect(url_for("index"))

    error = None
    if request.method == "POST":
        username = as_text("username").upper()
        password = request.form.get("password") or ""
        try:
            account = verify_admin_login(username, password)
        except Exception:
            account = None
            error = "Database is unavailable."
        if account:
            session.clear()
            session["account_id"] = int(account["id"])
            session["username"] = account["username"]
            session["gmlevel"] = int(account["gmlevel"] or 0)
            flash("Logged in.", "success")
            return redirect(safe_next_url(request.args.get("next")))
        if not error:
            error = "Invalid credentials or missing gmlevel."

    return render_template("login.html", error=error, status=server_status())


@app.route("/logout", methods=["POST"])
@require_login
def logout():
    session.clear()
    flash("Logged out.", "success")
    return redirect(url_for("login"))


@app.route("/accounts")
@require_login
def accounts():
    return render_template(
        "accounts/list.html",
        accounts=account_summary_rows(),
        expansion_names=EXPANSION_SHORT_NAMES,
        gm_levels=GM_LEVELS,
    )


@app.route("/characters")
@require_login
def characters():
    server_status()
    characters = character_rows()
    return render_template(
        "characters/list.html",
        characters=characters,
        character_factions=faction_counts(characters),
    )


@app.route("/accounts/new", methods=["GET", "POST"])
@require_login
def account_create():
    if request.method == "POST":
        username = as_text("username").upper()
        password = request.form.get("password") or ""
        email = as_text("email")
        expansion = as_int("expansion", 5)
        gmlevel = as_int("gmlevel", 0)

        if not username or not password:
            flash("Username and password are required.", "error")
            return render_template(
                "accounts/form.html",
                account=None,
                expansions=EXPANSIONS,
                banned=is_checked("banned"),
                gm_levels=GM_LEVELS,
                gmlevel=gmlevel,
            )

        account_id = insert_account(
            username,
            make_srp6_credentials(username, password),
            email,
            expansion,
        )

        if is_checked("banned"):
            set_account_banned(account_id, True, session.get("username", "WEB"))
        set_account_gmlevel(account_id, gmlevel)

        flash("Account created.", "success")
        return redirect(url_for("account_edit", account_id=account_id))

    return render_template(
        "accounts/form.html",
        account=None,
        expansions=EXPANSIONS,
        banned=False,
        gm_levels=GM_LEVELS,
        gmlevel=0,
    )


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
        gmlevel = as_int("gmlevel", get_account_gmlevel(account_id))
        password = request.form.get("password") or ""
        banned = is_checked("banned")

        if not username:
            flash("Username is required.", "error")
            return redirect(url_for("account_edit", account_id=account_id))

        password_data = make_srp6_credentials(username, password) if password else None
        update_account(account_id, username, email, expansion, password_data)

        if banned != is_account_banned(account_id):
            set_account_banned(account_id, banned, session.get("username", "WEB"))
        set_account_gmlevel(account_id, gmlevel)

        flash("Account updated.", "success")
        return redirect(url_for("account_edit", account_id=account_id))

    server_status()
    return render_template(
        "accounts/form.html",
        account=account,
        banned=is_account_banned(account_id),
        expansions=EXPANSIONS,
        gm_levels=GM_LEVELS,
        gmlevel=get_account_gmlevel(account_id),
        characters=account_characters(account_id),
    )


@app.post("/accounts/<int:account_id>/characters/<int:guid>/rename")
@require_login
def character_rename(account_id: int, guid: int):
    character = get_account_character(account_id, guid)
    if not character:
        flash("Character not found.", "error")
        return redirect(url_for("account_edit", account_id=account_id))

    name = as_text("name")
    if not name:
        flash("Character name is required.", "error")
        return redirect(url_for("account_edit", account_id=account_id))

    with db_cursor("characters") as (_conn, cursor):
        cursor.execute(
            "UPDATE characters SET name = %s WHERE account = %s AND guid = %s",
            (name, account_id, guid),
        )

    flash("Character renamed.", "success")
    return redirect(url_for("account_edit", account_id=account_id))


@app.post("/accounts/<int:account_id>/characters/<int:guid>/delete")
@require_login
def character_delete(account_id: int, guid: int):
    character = get_account_character(account_id, guid)
    if not character:
        flash("Character not found.", "error")
        return redirect(url_for("account_edit", account_id=account_id))

    delete_character_data(guid)
    flash("Character deleted.", "success")
    return redirect(url_for("account_edit", account_id=account_id))


@app.post("/accounts/<int:account_id>/delete")
@require_login
def account_delete(account_id: int):
    account = get_account(account_id)
    if not account:
        flash("Account not found.", "error")
        return redirect(url_for("accounts"))

    delete_account_characters(account_id)
    delete_account_auth_rows(account_id)

    if int(session.get("account_id") or 0) == account_id:
        session.clear()
        flash("Account deleted.", "success")
        return redirect(url_for("login"))

    flash("Account and related character data deleted.", "success")
    return redirect(url_for("accounts"))


@app.route("/realmlist")
@require_login
def realmlist():
    return render_template(
        "realmlist/list.html",
        realms=realm_rows(),
        realm_types=REALM_TYPES,
        motd=get_motd(),
    )


@app.post("/realmlist/motd")
@require_login
def realm_motd_update():
    save_motd(as_text("motd"))
    flash("MOTD updated.", "success")
    return redirect(url_for("realmlist"))


@app.route("/realmlist/new", methods=["GET", "POST"])
@require_login
def realm_create():
    if request.method == "POST":
        name = as_text("name")
        if not name:
            flash("Realm name is required.", "error")
            return render_template("realmlist/form.html", realm=None, realm_types=REALM_TYPES)

        insert_realm(name, as_int("icon", 1))
        flash("Realm created.", "success")
        return redirect(url_for("realmlist"))

    return render_template("realmlist/form.html", realm=None, realm_types=REALM_TYPES)


@app.route("/realmlist/<int:realm_id>/edit", methods=["GET", "POST"])
@require_login
def realm_edit(realm_id: int):
    realm = get_realm(realm_id)
    if not realm:
        flash("Realm not found.", "error")
        return redirect(url_for("realmlist"))

    if request.method == "POST":
        name = as_text("name")
        if not name:
            flash("Realm name is required.", "error")
            return redirect(url_for("realm_edit", realm_id=realm_id))

        update_realm(realm_id, name, as_int("icon", 1))
        flash("Realm updated.", "success")
        return redirect(url_for("realm_edit", realm_id=realm_id))

    return render_template("realmlist/form.html", realm=realm, realm_types=REALM_TYPES)


@app.post("/realmlist/<int:realm_id>/delete")
@require_login
def realm_delete(realm_id: int):
    delete_realm(realm_id)
    flash("Realm deleted.", "success")
    return redirect(url_for("realmlist"))


@app.route("/teleports")
@require_login
def teleports():
    return render_template("teleports/list.html", teleports=teleport_rows())


@app.post("/teleports/refresh")
@require_login
def teleport_refresh():
    try:
        load_teleport_cache()
    except Exception as exc:
        flash(f"Teleport cache refresh failed: {exc}", "error")
    else:
        flash("Teleport cache refreshed.", "success")
    return redirect(url_for("teleports"))


@app.route("/teleports/new", methods=["GET", "POST"])
@require_login
def teleport_create():
    if request.method == "POST":
        try:
            name = save_teleport()
        except ValueError as exc:
            flash(str(exc), "error")
            return render_template("teleports/form.html", teleport=None)
        flash("Teleport created.", "success")
        return redirect(url_for("teleport_edit", name=name))

    return render_template("teleports/form.html", teleport=None)


@app.route("/teleports/<path:name>/edit", methods=["GET", "POST"])
@require_login
def teleport_edit(name: str):
    teleport = get_teleport(name)
    if not teleport:
        flash("Teleport not found.", "error")
        return redirect(url_for("teleports"))

    if request.method == "POST":
        try:
            new_name = save_teleport(name)
        except ValueError as exc:
            flash(str(exc), "error")
            return redirect(url_for("teleport_edit", name=name))
        flash("Teleport updated.", "success")
        return redirect(url_for("teleport_edit", name=new_name))

    return render_template("teleports/form.html", teleport=teleport)


@app.post("/teleports/<path:name>/delete")
@require_login
def teleport_delete(name: str):
    delete_teleport(name)
    flash("Teleport deleted.", "success")
    return redirect(url_for("teleports"))


if __name__ == "__main__":
    warm_teleport_cache()
    app.run(host="0.0.0.0", port=5001, debug=True)
