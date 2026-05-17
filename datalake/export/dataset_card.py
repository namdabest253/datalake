"""Auto-generated dataset_card.md from SQL aggregates over a completed run.

See docs/04-data-model.md §dataset_card.md auto-generation.
"""

from __future__ import annotations

import json
from collections import Counter
from pathlib import Path

import aiosqlite

from datalake.storage.db import connect

DATASET_CARD_TEMPLATE = """\
# Datalake dataset card

- **Run ID**: {run_id}
- **Corpus version**: {corpus_version}
- **Docs total**: {docs_total}
- **Docs done**: {docs_done} ({pct_done:.1f}%)
- **Docs partial (catalog only)**: {docs_partial}
- **Docs failed**: {docs_failed}

## Catalog distribution
- Content types: {content_type_counts}
- Ownership: {ownership_counts}
- Commercial actions: {commercial_action_counts}
- License-ready docs: {license_ready_count} ({license_ready_pct:.1f}%)

## Label quality (vs single-pass GPT-4 on 200-doc eval subset)
- Datalake win rate: {win_rate_pct}
- Quality delta by dimension: {dimension_deltas}
- Datalake cost per doc: ${wafer_cost_per_doc:.4f}
- GPT-4 cost per doc: ${gpt4_cost_per_doc:.4f}
- Datalake / GPT-4 cost ratio: {cost_ratio}

## Models used
{model_versions_table}

## Methodology
Datalake ran a 6-pass agent loop (propose × 3 → critique × 3 → refine × 3 → vote → enrich)
on Wafer Serverless. GPT-4 baseline ran single-pass with the same combined prompt.
Judge: {judge_model}, blinded A/B comparison.

GPT-4 foil cost in the dashboard cost meter is **estimated** (tokens × public pricing);
GPT-4 was only actually run on the 200-doc eval subset. The human-labeler foil
($30–$60/paper Surge-tier rate per PRD §3) is reference-only — no human labels are produced.
"""


async def render_dataset_card(run_id: str, db_path: Path, out_path: Path) -> None:
    """Populate the template from SQL aggregates and write to out_path."""
    out_path.parent.mkdir(parents=True, exist_ok=True)
    async with connect(db_path) as conn:
        ctx = await _gather_aggregates(conn, run_id)
    out_path.write_text(DATASET_CARD_TEMPLATE.format(**ctx), encoding="utf-8")


async def _gather_aggregates(conn: aiosqlite.Connection, run_id: str) -> dict:
    """Collect every value the template references. Eval fields fall back to 'n/a'."""
    run_row = await (
        await conn.execute(
            "SELECT corpus_version, model_versions FROM runs WHERE id=?", (run_id,)
        )
    ).fetchone()
    corpus_version = run_row["corpus_version"] if run_row else "unknown"
    model_versions = _safe_json(run_row["model_versions"] if run_row else None, {})

    # Doc lifecycle counts.
    docs_done = await _count(conn, "documents", "run_id=? AND status='DONE' AND partial=0", (run_id,))
    docs_partial = await _count(conn, "documents", "run_id=? AND partial=1", (run_id,))
    docs_failed = await _count(conn, "documents", "run_id=? AND status='FAILED'", (run_id,))
    docs_total = docs_done + docs_partial + docs_failed
    pct_done = (docs_done / docs_total * 100.0) if docs_total else 0.0

    # Catalog histograms.
    content_type_counts = await _histogram(
        conn,
        "SELECT c.content_type AS k, COUNT(*) AS n FROM catalog_records c "
        "JOIN documents d ON d.id=c.doc_id WHERE d.run_id=? GROUP BY c.content_type",
        (run_id,),
    )
    ownership_counts = await _histogram(
        conn,
        "SELECT c.ownership AS k, COUNT(*) AS n FROM catalog_records c "
        "JOIN documents d ON d.id=c.doc_id WHERE d.run_id=? GROUP BY c.ownership",
        (run_id,),
    )
    commercial_action_counts = await _histogram(
        conn,
        "SELECT c.commercial_action AS k, COUNT(*) AS n FROM catalog_records c "
        "JOIN documents d ON d.id=c.doc_id WHERE d.run_id=? GROUP BY c.commercial_action",
        (run_id,),
    )
    license_ready_count = commercial_action_counts.get("license_ready", 0)
    license_ready_pct = (
        (license_ready_count / docs_done * 100.0) if docs_done else 0.0
    )

    # Cost per doc (from inference_calls). Avoid div-by-zero when docs_done=0.
    cost_row = await (
        await conn.execute(
            "SELECT "
            "  COALESCE(SUM(CASE WHEN provider='wafer'  AND cost_basis='actual'    "
            "                    THEN cost_micro_usd ELSE 0 END),0) AS wafer, "
            "  COALESCE(SUM(CASE WHEN provider='openai' AND cost_basis='estimated' "
            "                    THEN cost_micro_usd ELSE 0 END),0) AS gpt4 "
            "FROM inference_calls WHERE run_id=?",
            (run_id,),
        )
    ).fetchone()
    wafer_micro = int(cost_row["wafer"]) if cost_row else 0
    gpt4_micro = int(cost_row["gpt4"]) if cost_row else 0
    denom = docs_done or 1
    wafer_cost_per_doc = wafer_micro / 1_000_000 / denom
    gpt4_cost_per_doc = gpt4_micro / 1_000_000 / denom
    cost_ratio = (
        f"{wafer_cost_per_doc / gpt4_cost_per_doc:.4f}"
        if gpt4_cost_per_doc > 0
        else "n/a"
    )

    # Eval block — n/a if no judge has run.
    win_rate_pct, dimension_deltas, judge_model = await _eval_summary(conn, run_id)

    return {
        "run_id": run_id,
        "corpus_version": corpus_version,
        "docs_total": docs_total,
        "docs_done": docs_done,
        "pct_done": pct_done,
        "docs_partial": docs_partial,
        "docs_failed": docs_failed,
        "content_type_counts": _fmt_counts(content_type_counts),
        "ownership_counts": _fmt_counts(ownership_counts),
        "commercial_action_counts": _fmt_counts(commercial_action_counts),
        "license_ready_count": license_ready_count,
        "license_ready_pct": license_ready_pct,
        "win_rate_pct": win_rate_pct,
        "dimension_deltas": dimension_deltas,
        "wafer_cost_per_doc": wafer_cost_per_doc,
        "gpt4_cost_per_doc": gpt4_cost_per_doc,
        "cost_ratio": cost_ratio,
        "model_versions_table": _model_versions_table(model_versions),
        "judge_model": judge_model,
    }


async def _count(conn: aiosqlite.Connection, table: str, where: str, params: tuple) -> int:
    cur = await conn.execute(f"SELECT COUNT(*) AS n FROM {table} WHERE {where}", params)
    row = await cur.fetchone()
    return int(row["n"]) if row else 0


async def _histogram(conn: aiosqlite.Connection, sql: str, params: tuple) -> dict[str, int]:
    cur = await conn.execute(sql, params)
    return {r["k"]: int(r["n"]) for r in await cur.fetchall()}


async def _eval_summary(
    conn: aiosqlite.Connection, run_id: str
) -> tuple[str, str, str]:
    """Returns (win_rate_pct, dimension_deltas, judge_model) — 'n/a' until eval runs."""
    cur = await conn.execute(
        "SELECT r.winner, r.dimension_scores, r.judge_model "
        "FROM eval_results r JOIN eval_pairs p ON p.id=r.pair_id "
        "WHERE p.run_id=?",
        (run_id,),
    )
    rows = await cur.fetchall()
    if not rows:
        return "n/a (run `datalake eval` first)", "n/a", "n/a"

    decisive = [r for r in rows if r["winner"] in ("A", "B")]
    wins = sum(1 for r in decisive if r["winner"] == "A")  # blinding map joined elsewhere
    win_rate = (wins / len(decisive) * 100.0) if decisive else 0.0
    judge_model = rows[0]["judge_model"]

    # Dimension deltas: mean(a - b) per dimension.
    sums: Counter = Counter()
    counts: Counter = Counter()
    for r in rows:
        scores = _safe_json(r["dimension_scores"], {})
        for dim, val in scores.items():
            if isinstance(val, dict) and "a" in val and "b" in val:
                sums[dim] += int(val["a"]) - int(val["b"])
                counts[dim] += 1
    deltas = {dim: round(sums[dim] / counts[dim], 2) for dim in sums if counts[dim]}
    return f"{win_rate:.1f}%", _fmt_counts(deltas), judge_model


def _fmt_counts(d: dict) -> str:
    if not d:
        return "(none)"
    return ", ".join(f"{k}: {v}" for k, v in sorted(d.items()))


def _model_versions_table(mv: dict) -> str:
    if not mv:
        return "_(none recorded)_"
    lines = ["| Role | Model |", "|---|---|"]
    for k, v in sorted(mv.items()):
        lines.append(f"| {k} | {v} |")
    return "\n".join(lines)


def _safe_json(raw, default):
    if raw is None:
        return default
    try:
        return json.loads(raw)
    except (json.JSONDecodeError, TypeError):
        return default
