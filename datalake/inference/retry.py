"""Exponential backoff, rate-limit handling, and JSON repair.

Shared across all InferenceClient impls so retry/accounting/tracing live in one place.
See docs/05-inference-client.md §Retry strategy.
"""

from __future__ import annotations

import asyncio
import json
import random
import time
import uuid

import aiosqlite
from pydantic import BaseModel, ValidationError

from datalake.inference.accounting import (
    BudgetExceededError,
    check_budget,
    insert_gpt4_foil,
    is_paused,
)
from datalake.inference.base import CallResult, InferenceClient
from datalake.storage.models import InferenceCall

MAX_ATTEMPTS = 3


def backoff_delay(attempt: int) -> float:
    """Exponential backoff with jitter, capped at 60s."""
    return min(60.0, 0.5 * 2**attempt + random.random() * 0.3)


def _strip_code_fence(text: str) -> str:
    """Qwen non-thinking mode wraps JSON in ```json ... ``` fences. Strip them."""
    t = text.strip()
    if not t.startswith("```"):
        return t
    # Drop opening fence line (```json or ```).
    if "\n" in t:
        t = t.split("\n", 1)[1]
    else:
        t = t[3:]
    # Drop trailing fence.
    if t.rstrip().endswith("```"):
        t = t.rstrip()[:-3]
    return t.strip()


async def call_pass(
    client: InferenceClient,
    *,
    system: str,
    user: str,
    schema_model: type[BaseModel] | None = None,
    temperature: float = 0.5,
    timeout: float = 20.0,
    conn: aiosqlite.Connection,
    run_id: str,
    doc_id: str | None,
    ceiling_usd: float | None = None,
) -> tuple[CallResult, BaseModel | None]:
    """One pass-level call with HTTP retry, JSON repair, and full cost accounting.

    Returns (CallResult, parsed_model_instance_or_None).
    Raises BudgetExceededError, the last transient exception, or pydantic ValidationError.

    Side effects on success:
      - Inserts one inference_calls row (cost_basis='actual').
      - Inserts a GPT-4 foil row (cost_basis='estimated') IF provider=='wafer'.
      - Checks budget against ceiling_usd IF provided AND provider=='wafer'.
    """
    if is_paused():
        raise BudgetExceededError("Budget previously exceeded; pass --continue to resume.")

    json_schema = schema_model.model_json_schema() if schema_model is not None else None
    result: CallResult | None = None

    # HTTP attempt loop — transient retries only (429, 5xx, timeout).
    for attempt in range(MAX_ATTEMPTS):
        try:
            result = await client.call(
                system=system,
                user=user,
                json_schema=json_schema,
                temperature=temperature,
                timeout=timeout,
            )
            break
        except TimeoutError:
            if attempt < MAX_ATTEMPTS - 1:
                await asyncio.sleep(backoff_delay(attempt))
                continue
            raise
        except Exception as e:  # noqa: BLE001 — classify by status, re-raise non-retryable
            status = getattr(e, "status", None)
            retryable = status is not None and (status == 429 or status >= 500)
            if retryable and attempt < MAX_ATTEMPTS - 1:
                await asyncio.sleep(backoff_delay(attempt))
                continue
            raise

    assert result is not None, "internal: call loop exited without result or exception"

    # JSON parse + pydantic validation (with one repair retry).
    parsed: BaseModel | None = None
    if schema_model is not None:
        try:
            parsed = schema_model.model_validate_json(_strip_code_fence(result.response_text))
        except (json.JSONDecodeError, ValidationError, ValueError):
            repair_user = (
                f"{user}\n\n"
                "Your previous response was not valid JSON matching the schema. "
                "It returned:\n"
                f"```\n{result.response_text[:1000]}\n```\n"
                "Please return ONLY valid JSON matching the schema above. No prose, no markdown."
            )
            repair_result = await client.call(
                system=system,
                user=repair_user,
                json_schema=json_schema,
                temperature=0.0,
                timeout=timeout,
            )
            # If this raises, propagate — caller treats as pass failure.
            parsed = schema_model.model_validate_json(_strip_code_fence(repair_result.response_text))
            result = repair_result.model_copy(update={"retried": True})

    # Persist the inference_calls row (cost_basis='actual').
    await _insert_call_row(conn, result, run_id, doc_id)

    # Foil + budget — only for actual Wafer calls. OpenAI/Judge calls don't get a GPT-4 foil.
    if result.provider == "wafer":
        await insert_gpt4_foil(result, run_id, doc_id, conn)
        if ceiling_usd is not None:
            await check_budget(run_id, ceiling_usd, conn)

    return result, parsed


async def _insert_call_row(
    conn: aiosqlite.Connection, result: CallResult, run_id: str, doc_id: str | None
) -> None:
    from datalake.storage.db import insert_inference_call

    await insert_inference_call(
        conn,
        InferenceCall(
            id=str(uuid.uuid4()),
            doc_id=doc_id,
            run_id=run_id,
            provider=result.provider,
            model=result.model,
            cost_basis=result.cost_basis,
            tokens_in=result.tokens_in,
            tokens_out=result.tokens_out,
            cost_micro_usd=result.cost_micro_usd,
            latency_ms=result.latency_ms,
            status="RETRIED" if result.retried else "OK",
            started_at=time.time(),
        ),
    )
