"""PROPOSE pass — N parallel draft records per doc.

Default N=3 (configurable via Settings.n_proposers). Each proposer runs with a
different analytical lens (compliance / methodology / novelty) so the drafts
attack the document from distinct angles and the critique pass has real
disagreement to work with. Temperature 0.8 adds sampling diversity on top.
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

# Proposer indices are taken modulo this list, so N can be tuned (1 → 6+)
# without code change. With the default N=3, all three lenses run once.
PROPOSER_PERSONAS: list[dict[str, str]] = [
    {
        "role": "compliance-focused proposer agent",
        "guidance": (
            "Your lens: ownership and rights. Surface compliance signals aggressively. "
            "Cite specific document evidence for every FERPA, HIPAA, IRB, "
            "publisher-exclusivity, or grant-restriction flag you raise. When ownership "
            "is contested (faculty / institution / publisher / funder / joint), name the "
            "contesting parties explicitly in the rationale."
        ),
    },
    {
        "role": "methodology-focused proposer agent",
        "guidance": (
            "Your lens: methods and evidence. Prefer specific named techniques over "
            "general categories (e.g., 'fine-tuned BERT-base on SQuAD', not 'machine "
            "learning'). Pull exact statistical procedures, sample sizes, and "
            "experimental designs from the text. Flag vague methodology language in the "
            "rationale instead of papering over it."
        ),
    },
    {
        "role": "novelty-focused proposer agent",
        "guidance": (
            "Your lens: contribution claims. Extract the verbatim novelty statement "
            "(e.g., 'we show that...', 'our contribution is...', 'unlike prior work...') "
            "and quote it in the novelty_claim field. Distinguish incremental refinements "
            "from substantive new claims and be explicit in the rationale about which."
        ),
    },
]


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
    persona = PROPOSER_PERSONAS[proposer_idx % len(PROPOSER_PERSONAS)]
    system = build_system(
        role=f"{persona['role']} #{proposer_idx}",
        heuristics_yaml=heuristics_yaml,
        persona_addendum=f"\n\n{persona['guidance']}",
    )
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
