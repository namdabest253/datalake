"""aiosqlite connection helper. WAL mode mandatory.

See docs/04-data-model.md §Write/read pattern.
"""

from __future__ import annotations

import json
import time
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from pathlib import Path

import aiosqlite

from datalake.storage.models import CatalogRecord, InferenceCall, LabelPayload, TraceEvent

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


async def insert_run(
    conn: aiosqlite.Connection,
    run_id: str,
    code_commit: str,
    corpus_version: str,
    config_snapshot: str,
    model_versions: str,
) -> None:
    """Insert a run row and seed its dashboard_counters row at zero."""
    now = time.time()
    await conn.execute(
        "INSERT INTO runs (id, started_at, ended_at, code_commit, corpus_version, "
        "config_snapshot, model_versions) VALUES (?, ?, ?, ?, ?, ?, ?)",
        (run_id, now, None, code_commit, corpus_version, config_snapshot, model_versions),
    )
    await conn.execute(
        "INSERT INTO dashboard_counters (run_id, updated_at) VALUES (?, ?)",
        (run_id, now),
    )


async def insert_document(
    conn: aiosqlite.Connection,
    doc_id: str,
    run_id: str,
    source_path: str,
    source_hash: str,
    content_type_guess: str | None,
) -> None:
    """Insert a document row, idempotent on (run_id, source_hash)."""
    await conn.execute(
        "INSERT OR IGNORE INTO documents (id, run_id, source_path, source_hash, "
        "content_type_guess, ingested_at, status, partial, timeout) "
        "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
        (doc_id, run_id, source_path, source_hash, content_type_guess,
         time.time(), "INGESTED", 0, 0),
    )


async def update_document_status(
    conn: aiosqlite.Connection,
    doc_id: str,
    status: str,
    partial: bool = False,
    timeout_flag: bool = False,
) -> None:
    """Update a document's lifecycle status + partial/timeout flags."""
    await conn.execute(
        "UPDATE documents SET status=?, partial=?, timeout=? WHERE id=?",
        (status, 1 if partial else 0, 1 if timeout_flag else 0, doc_id),
    )


async def insert_catalog_record(conn: aiosqlite.Connection, catalog: CatalogRecord) -> None:
    """Persist a catalog record. JSON-encodes compliance_flags."""
    await conn.execute(
        "INSERT OR REPLACE INTO catalog_records (doc_id, content_type, "
        "content_type_confidence, ownership, ownership_confidence, ownership_rationale, "
        "compliance_flags, commercial_score, commercial_action) "
        "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
        (
            catalog.doc_id,
            catalog.content_type,
            catalog.content_type_confidence,
            catalog.ownership,
            catalog.ownership_confidence,
            catalog.ownership_rationale,
            json.dumps(catalog.compliance_flags),
            catalog.commercial_score,
            catalog.commercial_action,
        ),
    )


async def insert_label_payload(conn: aiosqlite.Connection, label: LabelPayload) -> None:
    """Persist a label payload. JSON-encodes all dict/list fields."""
    enriched = json.dumps(label.enriched_payload) if label.enriched_payload is not None else None
    await conn.execute(
        "INSERT OR REPLACE INTO label_payloads (doc_id, structured_abstract, methodology, "
        "novelty_claim, evidence_quality, claim_graph, citations, domain_tags, "
        "enriched_payload, partial) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
        (
            label.doc_id,
            json.dumps(label.structured_abstract),
            json.dumps(label.methodology),
            label.novelty_claim,
            json.dumps(label.evidence_quality),
            json.dumps(label.claim_graph),
            json.dumps(label.citations),
            json.dumps(label.domain_tags),
            enriched,
            1 if label.partial else 0,
        ),
    )


async def insert_trace_event(conn: aiosqlite.Connection, event: TraceEvent) -> None:
    """Persist a trace event. JSON-encodes prompt_ref/response_ref when present."""
    prompt_ref = json.dumps(event.prompt_ref) if event.prompt_ref is not None else None
    response_ref = json.dumps(event.response_ref) if event.response_ref is not None else None
    await conn.execute(
        "INSERT INTO trace_events (id, doc_id, run_id, pass, proposal_idx, parent_event_id, "
        "started_at, ended_at, status, prompt_ref, response_ref, tokens_in, tokens_out, "
        "cost_micro_usd) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
        (
            event.id,
            event.doc_id,
            event.run_id,
            event.pass_,
            event.proposal_idx,
            event.parent_event_id,
            event.started_at,
            event.ended_at,
            event.status,
            prompt_ref,
            response_ref,
            event.tokens_in,
            event.tokens_out,
            event.cost_micro_usd,
        ),
    )


async def insert_inference_call(conn: aiosqlite.Connection, call: InferenceCall) -> None:
    """Persist an inference call ledger row."""
    await conn.execute(
        "INSERT INTO inference_calls (id, doc_id, run_id, provider, model, cost_basis, "
        "tokens_in, tokens_out, cost_micro_usd, latency_ms, status, started_at) "
        "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
        (
            call.id,
            call.doc_id,
            call.run_id,
            call.provider,
            call.model,
            call.cost_basis,
            call.tokens_in,
            call.tokens_out,
            call.cost_micro_usd,
            call.latency_ms,
            call.status,
            call.started_at,
        ),
    )


_COST_SET_CLAUSE = (
    "total_wafer_micro_usd = total_wafer_micro_usd + ?, "
    "total_gpt4_equivalent_micro_usd = total_gpt4_equivalent_micro_usd + ?, "
    "total_human_labeler_equivalent_micro_usd = total_human_labeler_equivalent_micro_usd + ?"
)


async def _bump_counter(
    conn: aiosqlite.Connection, run_id: str, counter_col: str, costs: tuple[int, int, int]
) -> None:
    """Atomically increment one counter column and add per-doc costs."""
    sql = (
        f"UPDATE dashboard_counters SET {counter_col} = {counter_col} + 1, "
        f"{_COST_SET_CLAUSE}, updated_at=? WHERE run_id=?"
    )
    await conn.execute(sql, (*costs, time.time(), run_id))


async def update_dashboard_counters_on_doc_done(
    conn: aiosqlite.Connection,
    run_id: str,
    doc_wafer_micro_usd: int,
    doc_gpt4_micro_usd: int,
    doc_human_labeler_micro_usd: int,
    doc_confidence: float,
    partial: bool = False,
    failed: bool = False,
) -> None:
    """Increment counters + cost totals; running-mean confidence on success.

    Self-healing: seeds a zero-valued counter row if one doesn't already exist for
    this run_id (e.g., when insert_run was called by an older code path that
    didn't seed it). All counter UPDATEs below then target an existing row.
    """
    await conn.execute(
        "INSERT OR IGNORE INTO dashboard_counters (run_id, updated_at) VALUES (?, ?)",
        (run_id, time.time()),
    )
    costs = (doc_wafer_micro_usd, doc_gpt4_micro_usd, doc_human_labeler_micro_usd)
    if failed:
        await _bump_counter(conn, run_id, "docs_failed", costs)
        return
    if partial:
        await _bump_counter(conn, run_id, "docs_partial", costs)
        return
    cursor = await conn.execute(
        "SELECT docs_done, avg_overall_confidence FROM dashboard_counters WHERE run_id=?",
        (run_id,),
    )
    row = await cursor.fetchone()
    old_done, old_avg = (row[0], row[1]) if row else (0, 0.0)
    new_avg = (old_avg * old_done + doc_confidence) / (old_done + 1)
    sql = (
        f"UPDATE dashboard_counters SET docs_done = docs_done + 1, {_COST_SET_CLAUSE}, "
        "avg_overall_confidence=?, updated_at=? WHERE run_id=?"
    )
    await conn.execute(sql, (*costs, new_avg, time.time(), run_id))


async def get_inference_call_sum(
    conn: aiosqlite.Connection,
    run_id: str,
    provider: str,
    cost_basis: str,
) -> int:
    """Sum cost_micro_usd for inference calls matching (run_id, provider, cost_basis)."""
    cursor = await conn.execute(
        "SELECT COALESCE(SUM(cost_micro_usd), 0) FROM inference_calls "
        "WHERE run_id=? AND provider=? AND cost_basis=?",
        (run_id, provider, cost_basis),
    )
    row = await cursor.fetchone()
    return int(row[0]) if row else 0
