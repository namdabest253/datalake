"""Token counting, cost accounting, GPT-4 + human-labeler foils, hard kill switch.

See docs/05-inference-client.md §Competitive foils and §Hard kill switch.
"""

from __future__ import annotations

import time
import uuid

import aiosqlite

from datalake.inference.base import CallResult
from datalake.storage.models import InferenceCall

# ---------------------------------------------------------------------------
# Pricing constants
# ---------------------------------------------------------------------------

GPT4_PRICING: dict[str, dict[str, float]] = {
    "gpt-4-turbo": {"input_per_million": 10.0, "output_per_million": 30.0},
}

# Wafer pricing — PLACEHOLDER. Update when actual Wafer Serverless pricing is known.
# The thesis (PRD §3) is "fractions of a cent per document" — chosen here to fit that
# envelope across an 11-call agent loop on ~3k-token inputs (~$0.0001 per call).
WAFER_PRICING: dict[str, dict[str, float]] = {
    "qwen-3.5-397b": {"input_per_million": 0.10, "output_per_million": 0.20},
    "qwen-3.5-strong": {"input_per_million": 0.30, "output_per_million": 0.60},
}

# Human-labeler foil — Surge/Scale midpoint per PRD §3 (~$30–$60/paper expert annotation).
# Per-doc, not per-call: a human costs the same whether the loop fires 1 call or 100.
HUMAN_LABELER_PRICING_PER_DOC_USD: dict[str, float] = {
    "research_paper": 50.0,
    "grant_proposal": 30.0,
    "dataset_description": 75.0,
    "faculty_publication": 50.0,
    "other": 20.0,
}


def estimate_gpt4_cost(tokens_in: int, tokens_out: int, model: str = "gpt-4-turbo") -> int:
    """Return estimated GPT-4 cost in micro-USD (integer to avoid float drift)."""
    p = GPT4_PRICING[model]
    usd = (tokens_in * p["input_per_million"] + tokens_out * p["output_per_million"]) / 1_000_000
    return int(usd * 1_000_000)


def estimate_wafer_cost(tokens_in: int, tokens_out: int, model: str) -> int:
    """Return estimated Wafer cost in micro-USD. Used for per-call billing on actual calls."""
    p = WAFER_PRICING.get(model, WAFER_PRICING["qwen-3.5-397b"])
    usd = (tokens_in * p["input_per_million"] + tokens_out * p["output_per_million"]) / 1_000_000
    return int(usd * 1_000_000)


# ---------------------------------------------------------------------------
# Foil insertion
# ---------------------------------------------------------------------------


async def insert_gpt4_foil(
    call: CallResult, run_id: str, doc_id: str | None, conn: aiosqlite.Connection
) -> None:
    """For every Wafer call on the main run, insert a parallel estimated GPT-4 row.

    Dashboard cost meter sums by provider so both totals are visible.
    """
    from datalake.storage.db import insert_inference_call  # local import — avoids cycle

    foil_cost = estimate_gpt4_cost(call.tokens_in, call.tokens_out)
    foil_call = InferenceCall(
        id=str(uuid.uuid4()),
        doc_id=doc_id,
        run_id=run_id,
        provider="openai",
        model="gpt-4-turbo",
        cost_basis="estimated",
        tokens_in=call.tokens_in,
        tokens_out=call.tokens_out,
        cost_micro_usd=foil_cost,
        latency_ms=0,
        status="OK",
        started_at=time.time(),
    )
    await insert_inference_call(conn, foil_call)


async def increment_human_labeler_foil(
    doc_content_type: str, run_id: str, conn: aiosqlite.Connection
) -> None:
    """Per-doc increment of the human-labeler foil counter.

    Reference-only — no human labels are produced. The Surge/Scale rate × doc count
    is the third row on the cost meter (docs/06-dashboard.md §Panel 4).
    """
    micro_usd = int(
        HUMAN_LABELER_PRICING_PER_DOC_USD.get(
            doc_content_type, HUMAN_LABELER_PRICING_PER_DOC_USD["other"]
        )
        * 1_000_000
    )
    await conn.execute(
        "UPDATE dashboard_counters "
        "SET total_human_labeler_equivalent_micro_usd = "
        "    total_human_labeler_equivalent_micro_usd + ?, "
        "    updated_at = ? "
        "WHERE run_id = ?",
        (micro_usd, time.time(), run_id),
    )


# ---------------------------------------------------------------------------
# Hard kill switch
# ---------------------------------------------------------------------------


class BudgetExceededError(RuntimeError):
    """Raised when cumulative Wafer spend exceeds wafer_spend_ceiling_usd."""


_paused: bool = False


def is_paused() -> bool:
    return _paused


def set_paused(paused: bool) -> None:
    global _paused
    _paused = paused


async def check_budget(run_id: str, ceiling_usd: float, conn: aiosqlite.Connection) -> None:
    """Sum wafer-provider actual spend for this run; raise if it exceeds ceiling.

    Called from the inference wrapper after every Wafer call.
    """
    from datalake.storage.db import get_inference_call_sum  # local import — avoids cycle

    total_micro = await get_inference_call_sum(conn, run_id, "wafer", "actual")
    if total_micro / 1_000_000 > ceiling_usd:
        set_paused(True)
        raise BudgetExceededError(
            f"Wafer spend ${total_micro / 1_000_000:.4f} exceeded ceiling ${ceiling_usd:.2f}. "
            "Re-run with `--continue --ceiling <higher>` to resume."
        )


# ---------------------------------------------------------------------------
# Local token counting (sanity check; trust API-reported usage on success)
# ---------------------------------------------------------------------------


def count_tokens_local(text: str, model: str = "gpt-4") -> int:
    """Approximate input token count locally before the call returns.

    Wafer uses Qwen, so this is an approximation. Discrepancies under ~20% are fine
    for the cost meter; flag if larger. Falls back to char/4 if tiktoken fails.
    """
    try:
        import tiktoken

        enc = tiktoken.encoding_for_model(model)
        return len(enc.encode(text))
    except (ImportError, KeyError, Exception):  # noqa: BLE001 — fallback, never raise
        return max(1, len(text) // 4)
