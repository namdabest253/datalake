"""ENRICH pass — produce the AI-lab-ready payload (claim graph, citation context, etc.).

Operates on the vote winner + full document context. Temperature 0.5.
On failure: catalog-only emit, label_payload.enriched_payload=null, partial=True.
See docs/02 §Per-pass contract, docs/03 §ENRICH prompt.
"""

from __future__ import annotations

import aiosqlite

from datalake.inference.base import CallResult, InferenceClient
from datalake.inference.retry import call_pass
from datalake.prompts.templates import (
    PASS_TEMPERATURE,
    EnrichedPayload,
    RefinedRecord,
    build_enrich_user,
    build_system,
)
from datalake.storage.models import Document


async def enrich(
    doc: Document,
    winning_refined: RefinedRecord,
    client: InferenceClient,
    heuristics_yaml: str,
    *,
    conn: aiosqlite.Connection,
    run_id: str,
    ceiling_usd: float | None = None,
) -> tuple[CallResult, EnrichedPayload]:
    """One enrichment call. Failure should NOT fail the doc — caller marks partial=True."""
    system = build_system("enrichment agent", heuristics_yaml)
    user = build_enrich_user(winning_refined, doc.text or "")
    call_result, parsed = await call_pass(
        client,
        system=system,
        user=user,
        schema_model=EnrichedPayload,
        temperature=PASS_TEMPERATURE["enrich"],
        timeout=25.0,  # ENRICH has the largest output budget
        conn=conn,
        run_id=run_id,
        doc_id=doc.id,
        ceiling_usd=ceiling_usd,
    )
    assert isinstance(parsed, EnrichedPayload)
    return call_result, parsed
