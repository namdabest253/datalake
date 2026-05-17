"""VOTE pass — consensus selection across surviving refined records.

Single call sees all refined records. Temperature 0.0 (deterministic).
Retry once on failure; second failure degrades to highest-confidence refined.
See docs/02 §Partial-failure policy.
"""

from __future__ import annotations

from datalake.inference.base import InferenceClient
from datalake.prompts.templates import RefinedRecord, VoteResult
from datalake.storage.models import Document


async def vote(
    doc: Document,
    refined: list[RefinedRecord],
    client: InferenceClient,
) -> VoteResult:
    """One consensus call. Caller handles retry-once and degradation policy."""
    raise NotImplementedError(
        "TODO: build VOTE prompt with all refined records, call client at temperature=0.0."
    )


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
