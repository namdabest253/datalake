"""Wafer Serverless client. Runs every pass of the agent loop.

See docs/05-inference-client.md.
"""

from __future__ import annotations

from lakeaudit.inference.base import CallResult, GlobalSemaphores


class WaferClient:
    """Implements the InferenceClient protocol against Wafer's HTTP API."""

    def __init__(
        self,
        api_key: str,
        base_url: str,
        model: str,
        semaphores: GlobalSemaphores,
    ) -> None:
        self.api_key = api_key
        self.base_url = base_url
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
        """Single Wafer call.

        Should acquire self.semaphores.wafer (provider gate), then delegate to
        lakeaudit.inference.retry.call_with_retry_and_accounting which handles
        backoff, JSON repair, rate-limit handling, and inference_calls insertion.
        """
        raise NotImplementedError(
            "TODO: build the request, acquire wafer semaphore, call with retry wrapper. "
            "Prefer Wafer JSON-schema response_format if supported; otherwise prompt + repair. "
            "See docs/03-prompts-and-schemas.md §Structured-output strategy."
        )
