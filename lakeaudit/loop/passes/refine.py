"""REFINE pass — apply critique to proposal. 1:1 with surviving (proposal, critique) pairs.

Temperature 0.2 — mostly mechanical merge. See docs/02 §Per-pass contract, docs/03 §REFINE.
"""

from __future__ import annotations

from lakeaudit.inference.base import InferenceClient
from lakeaudit.prompts.templates import Critique, ProposalRecord, RefinedRecord
from lakeaudit.storage.models import Document


async def refine(
    doc: Document,
    proposal: ProposalRecord,
    critique: Critique,
    client: InferenceClient,
) -> RefinedRecord:
    """One refine call. Apply all 'wrong' / 'contradicted_by_source' critiques unconditionally."""
    raise NotImplementedError(
        "TODO: build REFINE prompt, call client at temperature=0.2, validate as RefinedRecord."
    )
