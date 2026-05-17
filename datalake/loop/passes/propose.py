"""PROPOSE pass — N parallel draft records per doc.

Default N=3 (configurable via Settings.n_proposers).
Temperature 0.8 for diverse drafts.
See docs/02-agent-loop.md and docs/03-prompts-and-schemas.md §PROPOSE prompt.
"""

from __future__ import annotations

import aiosqlite

from datalake.inference.base import CallResult, InferenceClient
from datalake.inference.retry import call_pass
from datalake.prompts.templates import (
    PASS_TEMPERATURE,
    TOKEN_BUDGETS,
    ProposalRecord,
    build_propose_user,
    build_system,
)
from datalake.storage.models import Document


async def propose(
    doc: Document,
    proposer_idx: int,
    client: InferenceClient,
    heuristics_yaml: str,
    *,
    conn: aiosqlite.Connection,
    run_id: str,
    ceiling_usd: float | None = None,
) -> tuple[CallResult, ProposalRecord]:
    """One proposer call. Caller fan-outs N of these in parallel.

    Returns (CallResult, ProposalRecord). The state machine uses the CallResult
    to write the trace event with token/cost/latency, and the ProposalRecord
    flows downstream into critique.
    """
    system = build_system(f"proposer agent #{proposer_idx}", heuristics_yaml)
    user = build_propose_user(
        doc.text or "",
        doc.references,
        doc.content_type_guess or "unknown",
    )
    call_result, parsed = await call_pass(
        client,
        system=system,
        user=user,
        schema_model=ProposalRecord,
        temperature=PASS_TEMPERATURE["propose"],
        timeout=20.0,
        max_tokens=TOKEN_BUDGETS["propose"]["output_cap"],
        conn=conn,
        run_id=run_id,
        doc_id=doc.id,
        ceiling_usd=ceiling_usd,
    )
    assert isinstance(parsed, ProposalRecord)  # narrow for type-checker
    return call_result, parsed
