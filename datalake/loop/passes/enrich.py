"""ENRICH pass — produce the AI-lab-ready payload (claim graph, citation context, etc.).

Operates on the vote winner + full document context. Temperature 0.5.
On failure: catalog-only emit, label_payload.enriched_payload=null, partial=True.
See docs/02 §Per-pass contract, docs/03 §ENRICH prompt.
"""

from __future__ import annotations

from datalake.inference.base import InferenceClient
from datalake.prompts.templates import EnrichedPayload, RefinedRecord
from datalake.storage.models import Document


async def enrich(
    doc: Document,
    winning_refined: RefinedRecord,
    client: InferenceClient,
) -> EnrichedPayload:
    """One enrichment call. Failure should NOT fail the doc — emit catalog-only with partial=True."""
    raise NotImplementedError(
        "TODO: build ENRICH prompt with winning record + full doc, call client at temperature=0.5, "
        "validate as EnrichedPayload."
    )
