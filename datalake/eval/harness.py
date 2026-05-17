"""Eval orchestrator: sample held-out docs, build (datalake, baseline) pairs,
run the judge, write a JSON report. See docs/07-evaluation.md §Pair construction.

Per user direction, the "GPT-4 baseline" is a SINGLE-PASS call against the
same Wafer model family — no real OpenAI spend. The GPT-4 cost figure
reported as `gpt4_cost_per_doc_micro_usd` is computed from observed token
counts × published GPT-4 rates and persisted to `inference_calls` with
`provider="openai"`, `cost_basis="estimated"`. The dashboard's existing
"GPT-4 equivalent" counter is built on the same convention.
"""

from __future__ import annotations

import json
import random
import time
import uuid
from collections import defaultdict
from pathlib import Path

import aiosqlite
from loguru import logger
from pydantic import ValidationError

from datalake.config import Settings
from datalake.eval import scoring
from datalake.eval.judge_runner import run_judge, self_test
from datalake.inference.accounting import estimate_gpt4_cost
from datalake.inference.base import GlobalSemaphores
from datalake.inference.judge import JudgeClient
from datalake.inference.wafer import WaferClient
from datalake.prompts.templates import (
    PASS_TEMPERATURE,
    BaselineRecord,
    build_gpt4_baseline_user,
    build_system,
)
from datalake.storage.db import connect, insert_inference_call
from datalake.storage.models import InferenceCall


async def gpt4_single_pass(
    doc_row: aiosqlite.Row,
    document_text: str,
    references: list[dict],
    settings: Settings,
    baseline_client: WaferClient,
    heuristics_yaml: str,
    *,
    conn: aiosqlite.Connection,
    run_id: str,
) -> dict:
    """Single-pass baseline: one call → catalog + label + enriched in one shot.

    Records two inference_calls rows for the same wire call:
      - provider=wafer, cost_basis=actual — the real infra cost we paid.
      - provider=openai, cost_basis=estimated — what GPT-4 would have cost
        for the same token counts, used as the foil for `cost_ratio`.

    Returns the validated BaselineRecord as a dict.
    """
    system = build_system(role="single-pass label generator", heuristics_yaml=heuristics_yaml)
    user = build_gpt4_baseline_user(
        document_text=document_text,
        references=references,
        content_type_guess=doc_row["content_type_guess"] or "other",
    )

    cr = await baseline_client.call(
        system=system,
        user=user,
        json_schema=BaselineRecord.model_json_schema(),
        temperature=PASS_TEMPERATURE["baseline"],
        timeout=60.0,
    )

    # Persist actual Wafer cost row.
    started = time.time()
    await insert_inference_call(
        conn,
        InferenceCall(
            id=str(uuid.uuid4()),
            doc_id=doc_row["id"],
            run_id=run_id,
            provider="wafer",
            model=cr.model,
            cost_basis="actual",
            tokens_in=cr.tokens_in,
            tokens_out=cr.tokens_out,
            cost_micro_usd=cr.cost_micro_usd,
            latency_ms=cr.latency_ms,
            status="OK",
            started_at=started,
        ),
    )

    # Persist estimated GPT-4 foil row — used by compute_cost_ratio.
    await insert_inference_call(
        conn,
        InferenceCall(
            id=str(uuid.uuid4()),
            doc_id=doc_row["id"],
            run_id=run_id,
            provider="openai",
            model=settings.openai_baseline_model,
            cost_basis="estimated",
            tokens_in=cr.tokens_in,
            tokens_out=cr.tokens_out,
            cost_micro_usd=estimate_gpt4_cost(cr.tokens_in, cr.tokens_out),
            latency_ms=0,
            status="OK",
            started_at=started,
        ),
    )

    try:
        record = BaselineRecord.model_validate_json(cr.response_text)
    except ValidationError as e:
        raise RuntimeError(
            f"Baseline output failed schema validation for doc {doc_row['id']}: {e}"
        ) from e

    return record.model_dump(mode="json")


async def _materialize_datalake_record(
    conn: aiosqlite.Connection, doc_id: str
) -> dict | None:
    """Reconstruct a BaselineRecord-shaped dict from stored catalog + label rows.

    Returns None if either side is missing — the caller must run the loop fresh.
    The judge sees BOTH sides in the same shape (catalog + label + enriched),
    so it cannot guess which side is the loop output from shape alone.
    """
    cat_cur = await conn.execute(
        "SELECT * FROM catalog_records WHERE doc_id = ?", (doc_id,)
    )
    cat_row = await cat_cur.fetchone()
    lab_cur = await conn.execute(
        "SELECT * FROM label_payloads WHERE doc_id = ?", (doc_id,)
    )
    lab_row = await lab_cur.fetchone()
    if cat_row is None or lab_row is None:
        return None

    methodology = json.loads(lab_row["methodology"])
    evidence = json.loads(lab_row["evidence_quality"])
    enriched_raw = lab_row["enriched_payload"]
    enriched = json.loads(enriched_raw) if enriched_raw else {}

    return {
        "catalog": {
            "content_type": cat_row["content_type"],
            "content_type_confidence": cat_row["content_type_confidence"],
            "ownership": cat_row["ownership"],
            "ownership_confidence": cat_row["ownership_confidence"],
            "ownership_rationale": cat_row["ownership_rationale"],
            "compliance_flags": json.loads(cat_row["compliance_flags"]),
            "commercial_score": cat_row["commercial_score"],
            "commercial_action": cat_row["commercial_action"],
        },
        "label": {
            "structured_abstract": json.loads(lab_row["structured_abstract"]),
            "methodology_named": methodology.get("named", []),
            "methodology_other_freetext": methodology.get("other_freetext"),
            "novelty_claim": lab_row["novelty_claim"],
            "evidence_type": evidence.get("type", "mixed"),
            "evidence_strength": evidence.get("strength", "moderate"),
            "sample_size": evidence.get("sample_size"),
            "claim_graph": json.loads(lab_row["claim_graph"]),
            "citations": json.loads(lab_row["citations"]),
            "domain_tags": json.loads(lab_row["domain_tags"]),
        },
        "enriched": enriched,
        # We don't store the loop's overall_confidence, so synthesise from the
        # catalog confidences as a passable summary signal. Used in eval only.
        "overall_confidence": float(
            (cat_row["content_type_confidence"] + cat_row["ownership_confidence"]) / 2
        ),
    }


async def _sample_doc_ids(
    conn: aiosqlite.Connection, n: int, source_run_id: str | None = None
) -> list[str]:
    """Stratified sample of doc_ids by content_type_guess, capped at `n`.

    Pulls from all DONE docs (those with both catalog + label) across runs.
    If `source_run_id` is given, restrict to docs from that run.
    """
    sql = (
        "SELECT d.id AS doc_id, d.content_type_guess AS bucket "
        "FROM documents d "
        "JOIN catalog_records c ON c.doc_id = d.id "
        "JOIN label_payloads l ON l.doc_id = d.id "
        "WHERE d.status = 'DONE'"
    )
    params: tuple = ()
    if source_run_id is not None:
        sql += " AND d.run_id = ?"
        params = (source_run_id,)
    cur = await conn.execute(sql, params)
    rows = await cur.fetchall()
    if not rows:
        return []

    # Bucket by content_type_guess; if missing, dump into "other".
    buckets: dict[str, list[str]] = defaultdict(list)
    for r in rows:
        bucket = r["bucket"] or "other"
        buckets[bucket].append(r["doc_id"])
    for ids in buckets.values():
        random.shuffle(ids)

    # Round-robin draw from buckets until we have n (or run out).
    picked: list[str] = []
    keys = list(buckets.keys())
    while len(picked) < n and any(buckets[k] for k in keys):
        for k in keys:
            if not buckets[k]:
                continue
            picked.append(buckets[k].pop())
            if len(picked) >= n:
                break
    return picked


async def _doc_metadata(
    conn: aiosqlite.Connection, doc_id: str
) -> aiosqlite.Row | None:
    cur = await conn.execute(
        "SELECT id, run_id, source_path, source_hash, content_type_guess, ingested_at "
        "FROM documents WHERE id = ?",
        (doc_id,),
    )
    return await cur.fetchone()


async def run_eval(
    n: int,
    run_id: str,
    settings: Settings,
    *,
    baseline_client: WaferClient,
    judge: JudgeClient,
    heuristics_yaml: str,
    dry_run: bool = False,
    seed: int | None = None,
) -> dict:
    """Sample docs, build pairs (datalake, baseline), judge them, aggregate.

    Returns the report dict; also writes it to ./.datalake/eval_report_<run_id>.json
    unless `dry_run=True`.
    """
    if seed is not None:
        random.seed(seed)

    db_path = settings.paths.sqlite_db
    if not db_path.exists():
        raise FileNotFoundError(
            f"No SQLite DB at {db_path}. Run `datalake ingest` and `datalake run` first."
        )

    # Lazy import to avoid pulling parser deps unless we need them.
    from datalake.ingest.parser import _parse_one

    async with connect(db_path) as conn:
        # Materialise an eval-only run row so inference_calls/eval_pairs FKs resolve.
        await conn.execute(
            "INSERT OR IGNORE INTO runs (id, started_at, code_commit, corpus_version, "
            "config_snapshot, model_versions) VALUES (?, ?, ?, ?, ?, ?)",
            (
                run_id,
                time.time(),
                "eval-run",
                "eval",
                json.dumps({"loop": settings.wafer_loop_model,
                            "baseline": settings.baseline_model,
                            "judge": settings.judge_model}),
                json.dumps({
                    "loop": settings.wafer_loop_model,
                    "baseline": settings.baseline_model,
                    "judge": settings.judge_model,
                }),
            ),
        )
        await conn.commit()

        doc_ids = await _sample_doc_ids(conn, n=n)
        if not doc_ids:
            raise RuntimeError(
                "No DONE docs with both catalog + label found. "
                "Run `datalake run` first so there are records to evaluate."
            )

        logger.info("eval_sampled n_target={} n_picked={}", n, len(doc_ids))

        # Build pairs sequentially — one SQLite connection, baseline calls
        # serialise on the global Wafer semaphore.
        for doc_id in doc_ids:
            doc_row = await _doc_metadata(conn, doc_id)
            if doc_row is None:
                continue
            datalake_record = await _materialize_datalake_record(conn, doc_id)
            if datalake_record is None:
                logger.warning("skip doc_id={}: no stored loop record", doc_id)
                continue

            try:
                text, refs = _parse_one(Path(doc_row["source_path"]))
            except Exception as exc:  # noqa: BLE001
                logger.warning("skip doc_id={}: parse failed: {}", doc_id, exc)
                continue

            try:
                baseline_record = await gpt4_single_pass(
                    doc_row=doc_row,
                    document_text=text,
                    references=refs,
                    settings=settings,
                    baseline_client=baseline_client,
                    heuristics_yaml=heuristics_yaml,
                    conn=conn,
                    run_id=run_id,
                )
            except Exception as exc:  # noqa: BLE001 — drop the doc, keep going
                logger.warning("baseline failed for doc_id={}: {}", doc_id, exc)
                continue

            a_is_datalake = random.random() < 0.5
            pair_id = str(uuid.uuid4())
            await conn.execute(
                "INSERT INTO eval_pairs (id, run_id, doc_id, datalake_record, "
                "gpt4_record, a_is_datalake) VALUES (?, ?, ?, ?, ?, ?)",
                (
                    pair_id,
                    run_id,
                    doc_id,
                    json.dumps(datalake_record),
                    json.dumps(baseline_record),
                    1 if a_is_datalake else 0,
                ),
            )
            await conn.commit()

        # Run the judge self-test BEFORE the main judge loop. Abort on failure.
        await self_test(judge, heuristics_yaml=heuristics_yaml)

        # Score all pairs.
        await run_judge(run_id=run_id, judge=judge, heuristics_yaml=heuristics_yaml, conn=conn)

        # Aggregate.
        report = await _compose_report(conn, run_id=run_id, settings=settings)

    # Write the JSON report (skip on dry_run — caller wants stdout only).
    if not dry_run:
        out_path = Path("./.datalake") / f"eval_report_{run_id}.json"
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(json.dumps(report, indent=2, sort_keys=True))
        logger.info("eval_report_written path={}", out_path)

    return report


async def _compose_report(
    conn: aiosqlite.Connection,
    run_id: str,
    settings: Settings,
) -> dict:
    """Pull pair-level results and compute win_rate, per-dimension deltas, cost_ratio."""
    cur = await conn.execute(
        "SELECT p.id, p.a_is_datalake, r.winner, r.dimension_scores "
        "FROM eval_pairs p JOIN eval_results r ON r.pair_id = p.id "
        "WHERE p.run_id = ?",
        (run_id,),
    )
    rows = await cur.fetchall()

    pair_scores: list[dict] = []
    unblinded: list[str] = []
    for r in rows:
        a_is_dl = bool(r["a_is_datalake"])
        unblinded.append(scoring.resolve_winner(a_is_dl, r["winner"]))
        try:
            dims = json.loads(r["dimension_scores"])
        except (TypeError, json.JSONDecodeError):
            continue
        a_scores = {k: int(v["A"]) for k, v in dims.items() if isinstance(v, dict)}
        b_scores = {k: int(v["B"]) for k, v in dims.items() if isinstance(v, dict)}
        datalake_side = a_scores if a_is_dl else b_scores
        gpt4_side = b_scores if a_is_dl else a_scores
        pair_scores.append({"datalake": datalake_side, "gpt4": gpt4_side})

    win_rate = scoring.compute_win_rate(unblinded)
    dim_deltas = (
        scoring.compute_dimension_deltas(pair_scores) if pair_scores else {}
    )

    # Cost numbers — sum over inference_calls scoped to this eval run.
    cur = await conn.execute(
        "SELECT COALESCE(SUM(cost_micro_usd), 0) FROM inference_calls "
        "WHERE run_id = ? AND provider = 'wafer' AND cost_basis = 'actual'",
        (run_id,),
    )
    wafer_total = int((await cur.fetchone())[0])
    cur = await conn.execute(
        "SELECT COALESCE(SUM(cost_micro_usd), 0) FROM inference_calls "
        "WHERE run_id = ? AND provider = 'openai' AND cost_basis = 'estimated'",
        (run_id,),
    )
    gpt4_total = int((await cur.fetchone())[0])

    n_docs = max(1, len(rows))
    return {
        "run_id": run_id,
        "n_pairs": len(rows),
        "win_rate": round(win_rate, 4),
        "dimension_deltas": {k: round(v, 3) for k, v in dim_deltas.items()},
        "wafer_cost_per_doc_micro_usd": wafer_total // n_docs,
        "gpt4_cost_per_doc_micro_usd": gpt4_total // n_docs,
        "cost_ratio": round(
            scoring.compute_cost_ratio(wafer_total, gpt4_total), 4
        ),
        "judge_model": settings.judge_model,
        "loop_model": settings.wafer_loop_model,
        "baseline_model": settings.baseline_model,
        "notes": (
            "Baseline records are produced by a single-pass call on the same Wafer "
            "model family — the experimental variable is single-pass vs the full "
            "multi-pass loop. The 'gpt4' cost column is estimated from token counts "
            "× published GPT-4 rates; no real OpenAI API calls were made."
        ),
    }


# Module-level convenience: GlobalSemaphores from settings.
def make_semaphores(settings: Settings) -> GlobalSemaphores:
    return GlobalSemaphores(
        wafer=settings.wafer_concurrency,
        openai=settings.openai_concurrency,
        judge=settings.judge_concurrency,
    )
