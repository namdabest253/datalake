"""Wafer-hosted stronger model used as the eval judge.

Resolves PRD §15 #1 — Wafer-only is a better sponsor story. Must be DISTINCT
from wafer_loop_model so the judge doesn't share blind spots with the producer.

See docs/07-evaluation.md §Judge model.
"""

from __future__ import annotations

import time

import aiohttp

from datalake.inference.accounting import estimate_wafer_cost
from datalake.inference.base import CallResult, GlobalSemaphores


class JudgeAPIError(RuntimeError):
    def __init__(self, status: int, body: str) -> None:
        super().__init__(f"Judge HTTP {status}: {body[:200]}")
        self.status = status


class JudgeClient:
    """Wraps a Wafer model selected for eval scoring. Gated by the JUDGE semaphore."""

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
        temperature: float = 0.0,
        timeout: float = 20.0,
    ) -> CallResult:
        body: dict = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            "temperature": temperature,
            "max_tokens": 1500,
            # Qwen defaults to thinking mode (CoT in `reasoning_content`); that eats
            # the entire token budget before any JSON comes out. Same fix as
            # WaferClient — see discovery note in datalake/inference/wafer.py.
            "chat_template_kwargs": {"enable_thinking": False},
        }
        if json_schema is not None:
            body["response_format"] = {"type": "json_object"}

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

        async with self.semaphores.judge:
            t0 = time.perf_counter()
            async with aiohttp.ClientSession(
                timeout=aiohttp.ClientTimeout(total=timeout)
            ) as session:
                async with session.post(
                    f"{self.base_url}/chat/completions", json=body, headers=headers
                ) as resp:
                    text = await resp.text()
                    if resp.status >= 400:
                        raise JudgeAPIError(resp.status, text)
                    data = await resp.json(content_type=None)
            latency_ms = int((time.perf_counter() - t0) * 1000)

        choices = data.get("choices") or []
        msg = choices[0].get("message", {}) if choices else {}
        content = msg.get("content") or ""
        usage = data.get("usage") or {}
        tokens_in = int(usage.get("prompt_tokens") or max(1, len(user) // 4))
        tokens_out = int(usage.get("completion_tokens") or max(1, len(content) // 4))
        return CallResult(
            response_text=content,
            tokens_in=tokens_in,
            tokens_out=tokens_out,
            cost_micro_usd=estimate_wafer_cost(tokens_in, tokens_out, self.model),
            cost_basis="actual",
            latency_ms=latency_ms,
            model=self.model,
            provider="judge",
        )
