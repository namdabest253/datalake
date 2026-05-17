"""Exponential backoff, rate-limit handling, and JSON repair.

Shared across all InferenceClient impls so retry/accounting/tracing live in one place.
See docs/05-inference-client.md §Retry strategy.
"""

from __future__ import annotations

import random
from collections.abc import Awaitable, Callable

from datalake.inference.base import CallResult

MAX_ATTEMPTS = 3


def backoff_delay(attempt: int) -> float:
    """Exponential backoff with jitter, capped at 60s."""
    return min(60.0, 0.5 * 2**attempt + random.random() * 0.3)


async def call_with_retry_and_accounting(
    call_fn: Callable[[], Awaitable[CallResult]],
    *,
    parse_validate: Callable[[str], object] | None = None,
) -> CallResult:
    """Run call_fn with retries.

    Policy:
      - 429 / 5xx / network errors: exponential backoff, up to MAX_ATTEMPTS.
      - JSON parse / pydantic validation: one repair retry.
      - Non-429 4xx: do not retry.
      - Per-call timeout: counts as a failure; retry once if attempts remain.
    """
    raise NotImplementedError(
        "TODO: implement the retry loop, JSON repair, and inference_calls row insertion. "
        "See docs/05-inference-client.md §Retry strategy."
    )


async def repair_retry(
    call_fn: Callable[[str], Awaitable[CallResult]],
    bad_output: str,
) -> CallResult:
    """One-shot JSON repair: original messages + bad_output + 'please return valid JSON'."""
    raise NotImplementedError("TODO: implement repair retry")
