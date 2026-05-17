"""Sync SQLite reader for Streamlit panels.

The dashboard is a separate process from the loop writer; it only reads.
WAL mode (set by the writer at init_db time) allows concurrent reads.
"""

from __future__ import annotations

import sqlite3
from pathlib import Path
from typing import Any

import streamlit as st


@st.cache_resource
def db_path() -> Path:
    """Resolve the SQLite path once per Streamlit process. Cached across reruns."""
    from datalake.config import load_settings

    return load_settings().paths.sqlite_db


def _open(path: Path) -> sqlite3.Connection:
    conn = sqlite3.connect(str(path), isolation_level=None)
    conn.row_factory = sqlite3.Row
    return conn


def read(sql: str, **params: Any) -> list[sqlite3.Row]:
    """Run a SELECT with named (`:name`) parameters and fetch all rows.

    Returns [] (not None) if the DB file or any referenced table is missing,
    so panels can render an empty state without a try/except in every one.
    """
    path = db_path()
    if not path.exists():
        return []
    try:
        conn = _open(path)
        try:
            return conn.execute(sql, params).fetchall()
        finally:
            conn.close()
    except sqlite3.OperationalError:
        return []


def read_one(sql: str, **params: Any) -> sqlite3.Row | None:
    rows = read(sql, **params)
    return rows[0] if rows else None
