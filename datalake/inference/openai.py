"""OpenAI GPT-4 baseline. EVAL SUBSET ONLY.

GPT-4 actually runs only inside the eval harness (~200 docs). On the main run
the GPT-4 cost is estimated from token counts × public pricing — see
datalake/inference/accounting.py §insert_gpt4_foil.

See docs/05-inference-client.md §GPT-4 foil (per-call).
"""

from __future__ import annotations

import time

import aiohttp

from datalake.inference.accounting import estimate_gpt4_cost
from datalake.inference.base import CallResult, GlobalSemaphores


class OpenAIAPIError(RuntimeError):
    def __init__(self, status: int, body: str) -> None:
        super().__init__(f"OpenAI HTTP {status}: {body[:200]}")
        self.status = status


class OpenAIClient:
    """Real GPT-4 calls. Used only by the eval harness."""

    BASE_URL = "https://api.openai.com/v1"

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
            body["response_format"] = {"type": "json_object"}

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

        async with self.semaphores.openai:
            t0 = time.perf_counter()
            async with aiohttp.ClientSession(
                timeout=aiohttp.ClientTimeout(total=timeout)
            ) as session:
                async with session.post(
                    f"{self.BASE_URL}/chat/completions", json=body, headers=headers
                ) as resp:
                    text = await resp.text()
                    if resp.status >= 400:
                        raise OpenAIAPIError(resp.status, text)
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
            cost_micro_usd=estimate_gpt4_cost(tokens_in, tokens_out, self.model),
            cost_basis="actual",
            latency_ms=latency_ms,
            model=self.model,
            provider="openai",
        )
