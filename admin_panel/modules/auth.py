#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from __future__ import annotations

from server.modules.crypto.SRP6Crypto import SRP6Crypto

from admin_panel.modules.config import CONFIG
from admin_panel.modules.db import fetch_one


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
