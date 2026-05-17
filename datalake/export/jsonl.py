"""JSONL writer matching the export schema in docs/04-data-model.md.

Custom MVP schema — not pinned to Anthropic or OpenAI fine-tune format.
Resolves PRD §15 #4.
"""

from __future__ import annotations

import json
from pathlib import Path

import aiosqlite

from datalake.inference.accounting import HUMAN_LABELER_PRICING_PER_DOC_USD
from datalake.storage.db import connect


async def export_jsonl(run_id: str, db_path: Path, out_path: Path) -> int:
    """Write one JSON object per line for DONE docs. Returns row count.

    Schema: {id, source_path, source_hash, run_id, catalog{...}, label{...},
             trace_summary{...}, costs{wafer_usd, gpt4_equivalent_usd,
             human_labeler_equivalent_usd}, model_versions{...}}
    """
    out_path.parent.mkdir(parents=True, exist_ok=True)
    count = 0
    async with connect(db_path) as conn:
        model_versions = await _fetch_model_versions(conn, run_id)
        rows = await _fetch_doc_rows(conn, run_id)
        with out_path.open("w", encoding="utf-8") as fh:
            for r in rows:
                # Catalog row missing → loop didn't produce anything usable; skip.
                if r["content_type"] is None:
                    continue
                doc = {
                    "id": r["id"],
                    "source_path": r["source_path"],
                    "source_hash": r["source_hash"],
                    "run_id": r["run_id"],
                }
                catalog = _build_catalog(r)
                label = _build_label(r)
                costs = await _per_doc_costs(conn, doc["id"], r["content_type_guess"])
                trace_summary = await _per_doc_trace_summary(conn, doc["id"], bool(r["timeout"]))
                fh.write(render_row(doc, catalog, label, trace_summary, costs, model_versions))
                fh.write("\n")
                count += 1
    return count


def render_row(
    document: dict,
    catalog: dict,
    label: dict | None,
    trace_summary: dict,
    costs: dict,
    model_versions: dict,
) -> str:
    """Serialize one row as JSONL. Inputs match the SQL JOIN result shape."""
    return json.dumps(
        {
            "id": document["id"],
            "source_path": document["source_path"],
            "source_hash": document["source_hash"],
            "run_id": document["run_id"],
            "catalog": catalog,
            "label": label,
            "trace_summary": trace_summary,
            "costs": costs,
            "model_versions": model_versions,
        },
        ensure_ascii=False,
    )


# ---------------------------------------------------------------------------
# Internal helpers — small, single-purpose queries.
# ---------------------------------------------------------------------------


_DOC_JOIN_SQL = """
SELECT d.id, d.source_path, d.source_hash, d.run_id,
       d.partial AS doc_partial, d.timeout, d.content_type_guess,
       c.content_type, c.content_type_confidence,
       c.ownership, c.ownership_confidence, c.ownership_rationale,
       c.compliance_flags, c.commercial_score, c.commercial_action,
       l.structured_abstract, l.methodology, l.novelty_claim,
       l.evidence_quality, l.claim_graph, l.citations,
       l.domain_tags, l.enriched_payload, l.partial AS label_partial
FROM documents d
LEFT JOIN catalog_records c ON c.doc_id = d.id
LEFT JOIN label_payloads  l ON l.doc_id = d.id
WHERE d.run_id=? AND d.status='DONE'
ORDER BY d.ingested_at
"""


async def _fetch_model_versions(conn: aiosqlite.Connection, run_id: str) -> dict:
    cur = await conn.execute("SELECT model_versions FROM runs WHERE id=?", (run_id,))
    row = await cur.fetchone()
    if row is None or row["model_versions"] is None:
        return {}
    try:
        return json.loads(row["model_versions"])
    except json.JSONDecodeError:
        return {}


async def _fetch_doc_rows(conn: aiosqlite.Connection, run_id: str) -> list[aiosqlite.Row]:
    cur = await conn.execute(_DOC_JOIN_SQL, (run_id,))
    return await cur.fetchall()


def _build_catalog(r: aiosqlite.Row) -> dict:
    return {
        "content_type": r["content_type"],
        "content_type_confidence": r["content_type_confidence"],
        "ownership": r["ownership"],
        "ownership_confidence": r["ownership_confidence"],
        "ownership_rationale": r["ownership_rationale"],
        "compliance_flags": _safe_json(r["compliance_flags"], default=[]),
        "commercial_score": r["commercial_score"],
        "commercial_action": r["commercial_action"],
    }


def _build_label(r: aiosqlite.Row) -> dict | None:
    if r["structured_abstract"] is None:
        return None
    return {
        "structured_abstract": _safe_json(r["structured_abstract"], default={}),
        "methodology": _safe_json(r["methodology"], default={}),
        "novelty_claim": r["novelty_claim"],
        "evidence_quality": _safe_json(r["evidence_quality"], default={}),
        "claim_graph": _safe_json(r["claim_graph"], default=[]),
        "citations": _safe_json(r["citations"], default=[]),
        "domain_tags": _safe_json(r["domain_tags"], default=[]),
        "enriched_payload": _safe_json(r["enriched_payload"], default=None)
        if r["enriched_payload"] is not None
        else None,
        "partial": bool(r["label_partial"]),
    }


async def _per_doc_costs(
    conn: aiosqlite.Connection, doc_id: str, content_type_guess: str | None
) -> dict:
    cur = await conn.execute(
        "SELECT provider, cost_basis, COALESCE(SUM(cost_micro_usd), 0) AS total "
        "FROM inference_calls WHERE doc_id=? GROUP BY provider, cost_basis",
        (doc_id,),
    )
    wafer_micro = 0
    gpt4_micro = 0
    for row in await cur.fetchall():
        if row["provider"] == "wafer" and row["cost_basis"] == "actual":
            wafer_micro += int(row["total"])
        elif row["provider"] == "openai" and row["cost_basis"] == "estimated":
            gpt4_micro += int(row["total"])
    human_usd = HUMAN_LABELER_PRICING_PER_DOC_USD.get(
        content_type_guess or "other", HUMAN_LABELER_PRICING_PER_DOC_USD["other"]
    )
    return {
        "wafer_usd": round(wafer_micro / 1_000_000, 6),
        "gpt4_equivalent_usd": round(gpt4_micro / 1_000_000, 6),
        "human_labeler_equivalent_usd": float(human_usd),
    }


async def _per_doc_trace_summary(
    conn: aiosqlite.Connection, doc_id: str, doc_timeout: bool
) -> dict:
    cur = await conn.execute(
        'SELECT "pass" AS pass_, status, COUNT(*) AS n FROM trace_events '
        "WHERE doc_id=? GROUP BY pass, status",
        (doc_id,),
    )
    rows = await cur.fetchall()
    passes_completed = sorted({r["pass_"] for r in rows if r["status"] == "OK"})
    n_proposers_succeeded = sum(
        r["n"] for r in rows if r["pass_"] == "PROPOSE" and r["status"] == "OK"
    )
    # State machine retries VOTE once before degrading; ≥2 FAILED VOTE rows ⇒ degraded path.
    vote_failed = sum(
        r["n"] for r in rows if r["pass_"] == "VOTE" and r["status"] == "FAILED"
    )
    return {
        "passes_completed": passes_completed,
        "vote_degraded": vote_failed >= 2,
        "timeout": doc_timeout,
        "n_proposers_succeeded": int(n_proposers_succeeded),
    }


def _safe_json(raw: str | None, default):
    if raw is None:
        return default
    try:
        return json.loads(raw)
    except (json.JSONDecodeError, TypeError):
        return default
