"""Write helpers for the storage layer.

Insert `runs` and `documents` rows. Keeps the ingest CLI thin and avoids
spreading raw SQL across modules. See docs/04-data-model.md §Write/read pattern.
"""

from __future__ import annotations

import hashlib
import json
import subprocess
import time
import uuid
from pathlib import Path

from loguru import logger

from datalake.config import Settings
from datalake.storage.db import connect
from datalake.storage.models import Document


def _git_commit() -> str:
    """Best-effort git SHA at startup. Returns 'unknown' outside a git checkout."""
    try:
        out = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            check=True,
            capture_output=True,
            text=True,
            timeout=2,
        )
        return out.stdout.strip()
    except (subprocess.CalledProcessError, FileNotFoundError, subprocess.TimeoutExpired):
        return "unknown"


def _corpus_version(root: Path) -> str:
    """Stable hash of the input folder's file list. Two runs over the same corpus
    produce the same corpus_version even if content changed — by design, we
    capture per-file hashes in `documents.source_hash` separately.
    """
    if root.is_file():
        return f"sha256:{hashlib.sha256(str(root).encode()).hexdigest()[:16]}"
    h = hashlib.sha256()
    for p in sorted(root.rglob("*")):
        if p.is_file():
            h.update(str(p.relative_to(root)).encode())
    return f"sha256:{h.hexdigest()[:16]}"


def _config_snapshot(settings: Settings) -> str:
    """Resolved settings as JSON, secrets redacted."""
    data = settings.model_dump(mode="json")
    for k in ("wafer_api_key", "judge_api_key"):
        if data.get(k):
            data[k] = "REDACTED"
    return json.dumps(data, sort_keys=True)


def _model_versions(settings: Settings) -> str:
    return json.dumps(
        {
            "wafer": settings.wafer_loop_model,
            "judge": settings.judge_model,
            "openai": settings.openai_baseline_model,
        },
        sort_keys=True,
    )


async def insert_run(
    db_path: Path,
    settings: Settings,
    corpus_root: Path,
    run_id: str | None = None,
) -> str:
    """Insert a runs row. Returns the run_id (generated if not supplied)."""
    rid = run_id or str(uuid.uuid4())
    async with connect(db_path) as conn:
        await conn.execute(
            """
            INSERT INTO runs (id, started_at, code_commit, corpus_version,
                              config_snapshot, model_versions)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                rid,
                time.time(),
                _git_commit(),
                _corpus_version(corpus_root),
                _config_snapshot(settings),
                _model_versions(settings),
            ),
        )
        await conn.commit()
    logger.info("run_inserted run_id={}", rid)
    return rid


async def insert_documents(db_path: Path, docs: list[Document]) -> int:
    """Bulk-insert Documents. Skips rows that collide on UNIQUE(run_id, source_hash)
    so re-ingesting the same corpus into the same run is idempotent.

    Returns the number of rows actually written.
    """
    if not docs:
        return 0
    rows = [
        (
            d.id,
            d.run_id,
            d.source_path,
            d.source_hash,
            d.content_type_guess,
            d.ingested_at,
            d.status,
            int(d.partial),
            int(d.timeout),
        )
        for d in docs
    ]
    async with connect(db_path) as conn:
        cursor = await conn.executemany(
            """
            INSERT OR IGNORE INTO documents
                (id, run_id, source_path, source_hash, content_type_guess,
                 ingested_at, status, partial, timeout)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            rows,
        )
        written = cursor.rowcount
        await conn.commit()
    logger.info("documents_inserted requested={} written={}", len(docs), written)
    return written
