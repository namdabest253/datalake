"""CRITIQUE pass — one critic per proposal (1:1 with PROPOSE).

Per-proposal fan-out (not one critic-sees-all). More parallel, more visible in the
loop visualizer. Temperature 0.4. See docs/02 §Fan-out shape, docs/03 §CRITIQUE prompt.
"""

from __future__ import annotations

import aiosqlite

from datalake.inference.base import CallResult, InferenceClient
from datalake.inference.retry import call_pass
from datalake.prompts.templates import (
    PASS_TEMPERATURE,
    Critique,
    ProposalRecord,
    build_critique_user,
    build_system,
)
from datalake.storage.models import Document


async def critique(
    doc: Document,
    proposal: ProposalRecord,
    proposal_idx: int,
    n_total: int,
    client: InferenceClient,
    heuristics_yaml: str,
    *,
    conn: aiosqlite.Connection,
    run_id: str,
    ceiling_usd: float | None = None,
) -> tuple[CallResult, Critique]:
    """Critique one proposal. Fail → caller drops the proposal from refine."""
    system = build_system(
        f"critic agent #{proposal_idx} of {n_total} (focus: compliance flags)",
        heuristics_yaml,
    )
    user = build_critique_user(proposal, doc.text or "", proposal_idx, n_total)
    call_result, parsed = await call_pass(
        client,
        system=system,
        user=user,
        schema_model=Critique,
        temperature=PASS_TEMPERATURE["critique"],
        timeout=20.0,
        conn=conn,
        run_id=run_id,
        doc_id=doc.id,
        ceiling_usd=ceiling_usd,
    )
    assert isinstance(parsed, Critique)
    return call_result, parsed
