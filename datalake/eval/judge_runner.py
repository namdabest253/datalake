"""Calls the judge model on each (record_a, record_b) pair with blinded A/B.

Self-test required before each run: judge the canonical pair from
tests/fixtures/eval/canonical_pair.json and assert "Datalake wins,
methodology delta ≥ +2". See docs/07-evaluation.md §Self-test.
"""

from __future__ import annotations

import json
import time
from pathlib import Path

import aiosqlite
from loguru import logger
from pydantic import ValidationError

from datalake.inference.judge import JudgeClient
from datalake.prompts.templates import (
    PASS_TEMPERATURE,
    DimensionScore,
    JudgeOutput,
    build_judge_user,
    build_system,
)

CANONICAL_PAIR_PATH = Path("tests/fixtures/eval/canonical_pair.json")
RUBRIC_PATH = Path("datalake/eval/judge_rubric.yaml")


def _load_rubric() -> str:
    if RUBRIC_PATH.exists():
        return RUBRIC_PATH.read_text()
    logger.warning("rubric missing at {} — using bare schema only", RUBRIC_PATH)
    return ""


async def judge_pair(
    record_a: dict,
    record_b: dict,
    document_text: str,
    judge: JudgeClient,
    heuristics_yaml: str = "",
) -> JudgeOutput:
    """Single judge call. Returns the validated JudgeOutput schema."""
    rubric = _load_rubric()
    system = build_system(role="evaluation judge", heuristics_yaml=heuristics_yaml)
    user = build_judge_user(
        record_a=record_a,
        record_b=record_b,
        document_text=document_text,
        rubric_yaml=rubric,
    )
    cr = await judge.call(
        system=system,
        user=user,
        json_schema=JudgeOutput.model_json_schema(),
        temperature=PASS_TEMPERATURE["judge"],
        timeout=30.0,
    )
    try:
        return JudgeOutput.model_validate_json(cr.response_text)
    except ValidationError as e:
        raise RuntimeError(f"Judge output failed schema validation: {e}") from e


async def run_judge(
    run_id: str,
    judge: JudgeClient,
    heuristics_yaml: str,
    conn: aiosqlite.Connection,
) -> None:
    """Score every pair in eval_pairs for `run_id` that doesn't yet have a result row.

    The blinding map (eval_pairs.a_is_datalake) is NOT shown to the judge. The
    judge sees only record_a and record_b in the order stored.
    """
    cur = await conn.execute(
        """
        SELECT p.id, p.doc_id, p.datalake_record, p.gpt4_record, p.a_is_datalake,
               d.source_path
        FROM eval_pairs p
        JOIN documents d ON d.id = p.doc_id
        LEFT JOIN eval_results r ON r.pair_id = p.id
        WHERE p.run_id = ? AND r.pair_id IS NULL
        """,
        (run_id,),
    )
    rows = await cur.fetchall()
    logger.info("judge_pairs run_id={} pending={}", run_id, len(rows))

    # Re-parse the source doc for each pair (text isn't persisted, only path).
    from datalake.ingest.parser import _parse_one

    for row in rows:
        try:
            text, _refs = _parse_one(Path(row["source_path"]))
        except Exception as exc:  # noqa: BLE001
            logger.warning("judge skip pair_id={}: parse failed: {}", row["id"], exc)
            continue

        datalake_record = json.loads(row["datalake_record"])
        gpt4_record = json.loads(row["gpt4_record"])
        a_is_datalake = bool(row["a_is_datalake"])
        # The blinding decision: if a_is_datalake, put datalake into the A slot.
        record_a = datalake_record if a_is_datalake else gpt4_record
        record_b = gpt4_record if a_is_datalake else datalake_record

        try:
            out = await judge_pair(record_a, record_b, text, judge, heuristics_yaml)
        except Exception as exc:  # noqa: BLE001
            logger.warning("judge call failed pair_id={}: {}", row["id"], exc)
            continue

        dimension_scores = {
            dim: {"A": getattr(out.a_scores, dim), "B": getattr(out.b_scores, dim)}
            for dim in DimensionScore.model_fields
        }
        await conn.execute(
            "INSERT OR REPLACE INTO eval_results "
            "(pair_id, winner, dimension_scores, rationale, judge_model, completed_at) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            (
                row["id"],
                out.winner,
                json.dumps(dimension_scores),
                out.rationale,
                judge.model,
                time.time(),
            ),
        )
        await conn.commit()


async def self_test(judge: JudgeClient, heuristics_yaml: str = "") -> None:
    """Abort the eval run if the judge doesn't call the canonical pair correctly.

    Catches: judge model regression, prompt template corruption, blinding-map bugs.
    Asserts: winner == "A" AND a_scores.methodology_specificity - b_scores.methodology_specificity >= 2,
    where the fixture deliberately places the high-quality (Datalake) record as A.
    """
    if not CANONICAL_PAIR_PATH.exists():
        raise FileNotFoundError(
            f"Canonical pair missing at {CANONICAL_PAIR_PATH}. "
            "See docs/07-evaluation.md §Self-test for the expected fixture format."
        )
    pair = json.loads(CANONICAL_PAIR_PATH.read_text())
    out = await judge_pair(
        record_a=pair["datalake_record"],
        record_b=pair["gpt4_record"],
        document_text=pair["document_text"],
        judge=judge,
        heuristics_yaml=heuristics_yaml,
    )
    methodology_delta = (
        out.a_scores.methodology_specificity - out.b_scores.methodology_specificity
    )
    expected_min = pair.get("expected_judgement", {}).get("methodology_delta_minimum", 2)
    if out.winner != "A" or methodology_delta < expected_min:
        raise RuntimeError(
            f"Judge self-test FAILED. winner={out.winner!r}, "
            f"methodology_delta={methodology_delta} (need >= {expected_min}). "
            f"Judge rationale: {out.rationale[:300]}"
        )
    logger.info(
        "judge_self_test_ok winner={} methodology_delta={}",
        out.winner,
        methodology_delta,
    )
