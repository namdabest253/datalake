"""OpenAI GPT-4 baseline. EVAL SUBSET ONLY.

GPT-4 actually runs only inside the eval harness (~200 docs). On the main run
the GPT-4 cost is estimated from token counts × public pricing — see
lakeaudit/inference/accounting.py §insert_gpt4_foil.

See docs/05-inference-client.md §GPT-4 foil (per-call).
"""

from __future__ import annotations

from lakeaudit.inference.base import CallResult, GlobalSemaphores


class OpenAIClient:
    """Real GPT-4 calls. Used only by the eval harness."""

    def __init__(
        self,
        api_key: str,
        model: str,
        semaphores: GlobalSemaphores,
    ) -> None:
        self.api_key = api_key
        self.model = model
        self.semaphores = semaphores

    async def call(
        self,
        system: str,
        user: str,
        *,
        json_schema: dict | None = None,
        temperature: float = 0.5,
        timeout: float = 20.0,
    ) -> CallResult:
        raise NotImplementedError(
            "TODO: acquire openai semaphore, call OpenAI Chat Completions API, "
            "wrap with retry. cost_basis='actual' since this is real spend."
        )
