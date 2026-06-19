#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from __future__ import annotations

from flask import request


def as_int(name: str, default: int = 0) -> int:
    value = (request.form.get(name) or "").strip()
    if value == "":
        return default
    try:
        return int(value)
    except ValueError:
        return default


def as_float(name: str, default: float = 0.0) -> float:
    value = (request.form.get(name) or "").strip()
    if value == "":
        return default
    try:
        return float(value)
    except ValueError:
        return default


def as_text(name: str, default: str = "") -> str:
    return (request.form.get(name) or default).strip()


def is_checked(name: str) -> int:
    return 1 if request.form.get(name) else 0
