"""VOTE pass — consensus selection across surviving refined records.

Single call sees all refined records. Temperature 0.0 (deterministic).
Retry once on failure; second failure degrades to highest-confidence refined.
See docs/02 §Partial-failure policy.
"""

from __future__ import annotations

import aiosqlite

from datalake.inference.base import CallResult, InferenceClient
from datalake.inference.retry import call_pass
from datalake.prompts.templates import (
    PASS_TEMPERATURE,
    RefinedRecord,
    VoteResult,
    build_system,
    build_vote_user,
)
from datalake.storage.models import Document


async def vote(
    doc: Document,
    refined: list[RefinedRecord],
    client: InferenceClient,
    heuristics_yaml: str,
    *,
    conn: aiosqlite.Connection,
    run_id: str,
    ceiling_usd: float | None = None,
) -> tuple[CallResult, VoteResult]:
    """One consensus call. Caller handles retry-once and degradation policy."""
    system = build_system("vote/consensus agent", heuristics_yaml)
    user = build_vote_user(refined, doc.text or "")
    call_result, parsed = await call_pass(
        client,
        system=system,
        user=user,
        schema_model=VoteResult,
        temperature=PASS_TEMPERATURE["vote"],
        timeout=15.0,
        conn=conn,
        run_id=run_id,
        doc_id=doc.id,
        ceiling_usd=ceiling_usd,
    )
    assert isinstance(parsed, VoteResult)
    return call_result, parsed


def degrade_to_highest_confidence(refined: list[RefinedRecord]) -> VoteResult:
    """Fallback when vote fails twice — pick the refined record with highest overall_confidence."""
    if not refined:
        raise ValueError("Cannot degrade vote: no refined records available")
    winner_idx = max(range(len(refined)), key=lambda i: refined[i].overall_confidence)
    return VoteResult(
        winner_idx=winner_idx,
        winner_confidence=refined[winner_idx].overall_confidence,
        rationale="Vote pass failed twice; degraded to highest-confidence refined record.",
    )
