"""aiosqlite connection helper. WAL mode mandatory.

See docs/04-data-model.md §Write/read pattern.
"""

from __future__ import annotations

from contextlib import asynccontextmanager
from pathlib import Path
from typing import AsyncIterator

import aiosqlite

SCHEMA_PATH = Path(__file__).parent / "schema.sql"


async def init_db(db_path: Path, persist: bool = False) -> None:
    """Create the SQLite file and apply schema.

    If persist=False, the existing file is removed first — hackathon-pragmatic,
    no migrations infrastructure.
    """
    if not persist and db_path.exists():
        db_path.unlink()
        for suffix in (".db-wal", ".db-shm"):
            sidecar = db_path.with_suffix(db_path.suffix + suffix)
            if sidecar.exists():
                sidecar.unlink()
    db_path.parent.mkdir(parents=True, exist_ok=True)
    ddl = SCHEMA_PATH.read_text()
    async with aiosqlite.connect(db_path) as conn:
        await conn.executescript(ddl)
        await conn.commit()


@asynccontextmanager
async def connect(db_path: Path) -> AsyncIterator[aiosqlite.Connection]:
    """Open a connection with WAL mode + row factory.

    Caller is responsible for transaction boundaries.
    """
    async with aiosqlite.connect(db_path) as conn:
        await conn.execute("PRAGMA journal_mode = WAL;")
        await conn.execute("PRAGMA synchronous = NORMAL;")
        await conn.execute("PRAGMA foreign_keys = ON;")
        conn.row_factory = aiosqlite.Row
        yield conn
