"""Per-doc orchestrator: READ → PROPOSE×N → CRITIQUE×N → REFINE×N → VOTE → ENRICH.

See docs/02-agent-loop.md §State machine, §Partial-failure policy, §Cancellation & budget.
"""

from __future__ import annotations

import asyncio
from enum import StrEnum

from datalake.config import Settings
from datalake.inference.base import InferenceClient
from datalake.prompts.templates import (
    Critique,
    EnrichedPayload,
    ProposalRecord,
    RefinedRecord,
    VoteResult,
)
from datalake.storage.models import Document


class State(StrEnum):
    INIT = "INIT"
    READ = "READ"
    PROPOSE_FANOUT = "PROPOSE_FANOUT"
    CRITIQUE_FANOUT = "CRITIQUE_FANOUT"
    REFINE = "REFINE"
    VOTE = "VOTE"
    ENRICH = "ENRICH"
    DONE = "DONE"
    FAILED = "FAILED"


class DocResult:
    """Carries through whatever each pass produced. Filled in incrementally."""

    def __init__(self, doc: Document) -> None:
        self.doc = doc
        self.proposals: list[ProposalRecord] = []
        self.critiques: list[Critique] = []
        self.refined: list[RefinedRecord] = []
        self.vote: VoteResult | None = None
        self.enriched: EnrichedPayload | None = None
        self.state: State = State.INIT
        self.partial: bool = False
        self.timeout: bool = False
        self.vote_degraded: bool = False


async def run_doc(
    doc: Document,
    client: InferenceClient,
    settings: Settings,
    per_doc_sem: asyncio.Semaphore,
) -> DocResult:
    """Run one doc through the 6-pass loop with a 30s wall-clock budget.

    On TimeoutError, cancel all in-flight tasks via the task group, emit whatever
    completed with timeout=True. See docs/02-agent-loop.md §Cancellation & budget.
    """
    raise NotImplementedError(
        "TODO: implement the state machine. "
        "Use `async with asyncio.timeout(settings.per_doc_budget_seconds)` "
        "wrapping a TaskGroup. Apply the partial-failure policy from docs/02 §Partial-failure policy."
    )


# ---------------------------------------------------------------------------
# Trace utilities
# ---------------------------------------------------------------------------


def should_verbose_trace(doc_index: int, sample_k: int) -> bool:
    """True for every K-th doc (K=10 default). See docs/02 §Visualizer sampling."""
    return doc_index % sample_k == 0
