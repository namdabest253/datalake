"""PROPOSE pass — N parallel draft records per doc.

Default N=3 (configurable via Settings.n_proposers).
Temperature 0.8 for diverse drafts.
See docs/02-agent-loop.md and docs/03-prompts-and-schemas.md §PROPOSE prompt.
"""

from __future__ import annotations

from datalake.inference.base import InferenceClient
from datalake.prompts.templates import ProposalRecord
from datalake.storage.models import Document


async def propose(
    doc: Document,
    client: InferenceClient,
    heuristics_yaml: str,
    proposer_idx: int,
) -> ProposalRecord:
    """One proposer call. Caller fan-outs N of these in parallel."""
    raise NotImplementedError(
        "TODO: build system+user from datalake.prompts.templates, "
        "call client with temperature=0.8, validate response as ProposalRecord."
    )
