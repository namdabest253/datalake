"""Wafer-hosted stronger model used as the eval judge.

Resolves PRD §15 #1 — Wafer-only is a better sponsor story. Must be DISTINCT
from wafer_loop_model so the judge doesn't share blind spots with the producer.

See docs/07-evaluation.md §Judge model.
"""

from __future__ import annotations

from datalake.inference.base import CallResult, GlobalSemaphores


class JudgeClient:
    """Wraps a Wafer model selected for eval scoring."""

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
        temperature: float = 0.0,
        timeout: float = 20.0,
    ) -> CallResult:
        raise NotImplementedError(
            "TODO: acquire judge semaphore, call Wafer with judge_model. "
            "Output schema is JudgeOutput from datalake/prompts/templates.py."
        )
