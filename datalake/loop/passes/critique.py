"""CRITIQUE pass — one critic per proposal (1:1 with PROPOSE).

Per-proposal fan-out (not one critic-sees-all). More parallel, more visible in the
loop visualizer. Temperature 0.4. See docs/02 §Fan-out shape, docs/03 §CRITIQUE prompt.
"""

from __future__ import annotations

from datalake.inference.base import InferenceClient
from datalake.prompts.templates import Critique, ProposalRecord
from datalake.storage.models import Document


async def critique(
    doc: Document,
    proposal: ProposalRecord,
    proposal_idx: int,
    n_total: int,
    client: InferenceClient,
    heuristics_yaml: str,
) -> Critique:
    """Critique one proposal. Fail → caller drops the proposal from refine."""
    raise NotImplementedError(
        "TODO: build CRITIQUE prompt, call client, validate as Critique. "
        "Heuristics are injected at the system level — pay special attention to "
        "compliance flags (missed flags are the most expensive error)."
    )
