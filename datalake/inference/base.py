"""InferenceClient protocol + shared concurrency primitives.

See docs/05-inference-client.md §Provider abstraction and §Concurrency primitives.
"""

from __future__ import annotations

import asyncio
from typing import Protocol, runtime_checkable

from pydantic import BaseModel


class CallResult(BaseModel):
    response_text: str
    tokens_in: int
    tokens_out: int
    cost_micro_usd: int
    cost_basis: str  # "actual" | "estimated"
    latency_ms: int
    model: str
    provider: str
    retried: bool = False


@runtime_checkable
class InferenceClient(Protocol):
    """Common shape across Wafer, OpenAI, and judge clients.

    Implementations should call into datalake.inference.retry.call_with_retry_and_accounting
    rather than reinventing retry/JSON-repair/cost-row logic.
    """

    async def call(
        self,
        system: str,
        user: str,
        *,
        json_schema: dict | None = None,
        temperature: float = 0.5,
        timeout: float = 20.0,
        max_tokens: int = 1500,
    ) -> CallResult:
        ...


# ---------------------------------------------------------------------------
# Global semaphores — instantiated by the loop entrypoint from Settings.
# Provider-global gates protect against API rate limits across all docs.
# ---------------------------------------------------------------------------


class GlobalSemaphores:
    """Container for the provider-global concurrency gates.

    Acquisition order in call_with_retry_and_accounting: provider global → per-doc → call.
    This order avoids deadlock (every call acquires global first).
    """

    def __init__(self, wafer: int, openai: int, judge: int) -> None:
        self.wafer = asyncio.Semaphore(wafer)
        self.openai = asyncio.Semaphore(openai)
        self.judge = asyncio.Semaphore(judge)


def make_per_doc_semaphore(limit: int) -> asyncio.Semaphore:
    """Create a per-doc semaphore. Prevents one doc's inner fan-out from starving others."""
    return asyncio.Semaphore(limit)
