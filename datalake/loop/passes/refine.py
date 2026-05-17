"""REFINE pass — apply critique to proposal. 1:1 with surviving (proposal, critique) pairs.

Temperature 0.2 — mostly mechanical merge. See docs/02 §Per-pass contract, docs/03 §REFINE.
"""

from __future__ import annotations

import aiosqlite

from datalake.inference.base import CallResult, InferenceClient
from datalake.inference.retry import call_pass
from datalake.prompts.templates import (
    PASS_TEMPERATURE,
    TOKEN_BUDGETS,
    Critique,
    ProposalRecord,
    RefinedRecord,
    build_refine_user,
    build_system,
)
from datalake.storage.models import Document


async def refine(
    doc: Document,
    proposal: ProposalRecord,
    critique: Critique,
    client: InferenceClient,
    heuristics_yaml: str,
    *,
    conn: aiosqlite.Connection,
    run_id: str,
    ceiling_usd: float | None = None,
) -> tuple[CallResult, RefinedRecord]:
    """One refine call. Apply all 'wrong' / 'contradicted_by_source' critiques unconditionally."""
    system = build_system("refine agent", heuristics_yaml)
    user = build_refine_user(proposal, critique, doc.text or "")
    call_result, parsed = await call_pass(
        client,
        system=system,
        user=user,
        schema_model=RefinedRecord,
        temperature=PASS_TEMPERATURE["refine"],
        timeout=20.0,
        max_tokens=TOKEN_BUDGETS["refine"]["output_cap"],
        conn=conn,
        run_id=run_id,
        doc_id=doc.id,
        ceiling_usd=ceiling_usd,
    )
    assert isinstance(parsed, RefinedRecord)
    return call_result, parsed
