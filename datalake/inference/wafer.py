"""Wafer Serverless client. Runs every pass of the agent loop.

See docs/05-inference-client.md.
"""

from __future__ import annotations

import time

import aiohttp

from datalake.inference.accounting import estimate_wafer_cost
from datalake.inference.base import CallResult, GlobalSemaphores


class WaferAPIError(RuntimeError):
    """Raised when Wafer returns a non-2xx status. Carries .status for retry classification."""

    def __init__(self, status: int, body: str) -> None:
        super().__init__(f"Wafer HTTP {status}: {body[:200]}")
        self.status = status


class WaferClient:
    """Implements the InferenceClient protocol against Wafer's OpenAI-compatible HTTP API."""

    def __init__(
        self,
        api_key: str,
        base_url: str,
        model: str,
        semaphores: GlobalSemaphores,
    ) -> None:
        self.api_key = api_key
        self.base_url = base_url.rstrip("/")
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
        """Single Wafer call. Retry/JSON-repair/accounting handled by the wrapper in retry.py."""
        body: dict = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            "temperature": temperature,
            "max_tokens": 2500,
        }
        if json_schema is not None:
            # Always request JSON-mode; structured-schema strictness is opt-in by provider.
            body["response_format"] = {"type": "json_object"}

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

        async with self.semaphores.wafer:
            t0 = time.perf_counter()
            async with aiohttp.ClientSession(
                timeout=aiohttp.ClientTimeout(total=timeout)
            ) as session:
                async with session.post(
                    f"{self.base_url}/chat/completions", json=body, headers=headers
                ) as resp:
                    text = await resp.text()
                    if resp.status >= 400:
                        raise WaferAPIError(resp.status, text)
                    data = await resp.json(content_type=None)
            latency_ms = int((time.perf_counter() - t0) * 1000)

        content = data["choices"][0]["message"]["content"]
        usage = data.get("usage", {})
        tokens_in = int(usage.get("prompt_tokens", max(1, len(user) // 4)))
        tokens_out = int(usage.get("completion_tokens", max(1, len(content) // 4)))
        return CallResult(
            response_text=content,
            tokens_in=tokens_in,
            tokens_out=tokens_out,
            cost_micro_usd=estimate_wafer_cost(tokens_in, tokens_out, self.model),
            cost_basis="actual",
            latency_ms=latency_ms,
            model=self.model,
            provider="wafer",
        )
