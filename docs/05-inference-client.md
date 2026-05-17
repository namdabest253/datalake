# 05. Inference client

Provider abstraction, concurrency model, retry/rate-limit, token + cost accounting, GPT-4 foil mechanics, hard kill switch. Every other module depends on this.

## Provider abstraction (`datalake/inference/base.py`)

```python
from typing import Protocol, runtime_checkable
from pydantic import BaseModel

class CallResult(BaseModel):
    response_text: str
    tokens_in: int
    tokens_out: int
    cost_micro_usd: int
    cost_basis: str          # "actual" | "estimated"
    latency_ms: int
    model: str
    provider: str
    retried: bool = False

@runtime_checkable
class InferenceClient(Protocol):
    async def call(
        self,
        system: str,
        user: str,
        *,
        json_schema: dict | None = None,
        temperature: float = 0.5,
        timeout: float = 20.0,
    ) -> CallResult: ...
```

Concrete implementations:

- `WaferClient` (`datalake/inference/wafer.py`)
- `OpenAIClient` (`datalake/inference/openai.py`) — eval-subset only
- `JudgeClient` (`datalake/inference/judge.py`) — wraps Wafer with a different model

All three share the same `call_with_retry_and_accounting` wrapper in `datalake/inference/retry.py` so retry, JSON repair, rate-limit handling, and `inference_calls` row insertion live in one place.

## Concurrency primitives

Global semaphores (created in `datalake/inference/base.py`, sized from `config.yaml`):

| Semaphore | Default | Purpose |
|---|---|---|
| `WAFER_CONCURRENCY` | 64 | Caps total in-flight Wafer calls across all docs |
| `OPENAI_CONCURRENCY` | 8 | Caps GPT-4 baseline calls — much smaller because OpenAI rate limits are tighter |
| `JUDGE_CONCURRENCY` | 4 | Caps judge model calls |

Per-doc semaphore (created per-doc in the orchestrator):

| Semaphore | Default | Purpose |
|---|---|---|
| `PER_DOC_CONCURRENCY` | 8 | Prevents one doc's inner fan-out from starving others |

Acquisition order (in `call_with_retry_and_accounting`): provider global → per-doc → call. This order avoids deadlock: every call acquires the global first, the per-doc second, so no cycles.

## Retry strategy (`datalake/inference/retry.py`)

- **Transient errors (429, 5xx, network)**: exponential backoff with jitter. `delay = min(60, 0.5 * 2**attempt + random()*0.3)`. Max 3 attempts.
- **Honor `Retry-After` header** on 429 — sleep at least that long.
- **JSON parse / pydantic-validation failure**: one repair retry with original messages + bad output + `please return valid JSON matching the schema; no prose.` Then fail.
- **Non-429 4xx**: do not retry. Log and propagate as `FAILED`.
- **Timeout (per-call)**: count as a failure, retry once if attempts remain.

Retries don't double-count cost: the wrapper inserts one `inference_calls` row per **logical** call, with `status='RETRIED'` if it succeeded after retries, and accumulates the total tokens consumed across attempts.

## Rate-limit handling

When Wafer returns 429:

1. Sleep `max(Retry-After, backoff_delay)`.
2. Emit `WARN` trace event with reason `rate_limited`.
3. Continue retry loop.

If the wrapper hits the rate-limit ceiling repeatedly (e.g., 5 docs in a row each hit max retries), it sets a global `cooldown_until` timestamp and other docs voluntarily yield until that time. This prevents a thundering-herd on the next allowed window.

## Token accounting

- **On submit**: count input tokens locally with `tiktoken.encoding_for_model("gpt-4")` as an approximation (Wafer uses Qwen, so it's not exact, but close enough for cost-meter and budget purposes).
- **On success**: trust API-reported `usage` if present; otherwise rely on the local count + local output count.
- **Store both** in `inference_calls`: `tokens_in`, `tokens_out`. The discrepancy is fine for the demo; flag it if it ever exceeds ~20%.

## Competitive foils (the load-bearing decision)

The cost meter shows three lines so judges see the full economic picture from PRD §3:

1. **Wafer (actual)** — real cost of running the loop.
2. **GPT-4 (estimated)** — same workload at GPT-4 prices.
3. **Human labeler (estimated)** — same workload via Scale/Surge expert annotation at $30–$60/paper.

**Neither foil actually runs in the main loop.** Both are computed in code and inserted as estimated rows. GPT-4 actually runs only on the 200-doc eval subset; no human labeling step exists at all — the human foil is reference-only.

### GPT-4 foil (per-call)

For every Wafer call on the main run, insert a parallel estimated row:

```python
GPT4_PRICING = {"gpt-4-turbo": {"input_per_million": 10.0, "output_per_million": 30.0}}

def insert_gpt4_foil(call: CallResult, db) -> None:
    foil_cost = estimate_gpt4_cost(call.tokens_in, call.tokens_out)
    db.insert_inference_call(
        provider="openai", model="gpt-4-turbo", cost_basis="estimated",
        tokens_in=call.tokens_in, tokens_out=call.tokens_out,
        cost_micro_usd=foil_cost, latency_ms=0, status="OK", ...
    )
```

### Human-labeler foil (per-doc)

For every completed doc on the main run, increment `dashboard_counters.total_human_labeler_equivalent_micro_usd` by a per-content-type constant. PRD §3 establishes $30–$60 per scientific paper (Surge-tier expert rate); defaults in `datalake/inference/accounting.py`:

```python
HUMAN_LABELER_PRICING_PER_DOC_USD = {
    "research_paper":      50.0,   # Surge/Scale midpoint per PRD §3
    "grant_proposal":      30.0,
    "dataset_description": 75.0,
    "faculty_publication": 50.0,
    "other":               20.0,
}

async def increment_human_labeler_foil(doc_content_type: str, run_id: str, db):
    micro_usd = int(HUMAN_LABELER_PRICING_PER_DOC_USD[doc_content_type] * 1_000_000)
    await db.execute(
        "UPDATE dashboard_counters "
        "SET total_human_labeler_equivalent_micro_usd = total_human_labeler_equivalent_micro_usd + ? "
        "WHERE run_id = ?",
        (micro_usd, run_id),
    )
```

No per-call rows for this foil — a human labeler costs the same whether the agent loop fires 1 call or 100 per doc. Per-doc granularity is enough for the cost meter.

### Dashboard annotation (always visible)

The cost meter ([`06`](06-dashboard.md)) surfaces the methodology so judges aren't surprised:

> "Foils estimated, no real spend. GPT-4: tokens × public pricing. Human: $50/paper midpoint (Surge/Scale, PRD §3). GPT-4 actually runs only on the 200-doc eval subset; no human labels are produced."

GPT-4 actually runs only in the eval harness (`datalake/eval/harness.py`), ~200 docs, `cost_basis='actual'`. Nowhere else.

This is intentional. Running GPT-4 on 20k docs would burn $100k+ in real OpenAI credits. Running Scale/Surge on 20k docs would burn $1M+ and take weeks. Neither serves the demo.

## Timeouts

| Scope | Default | Where |
|---|---|---|
| Per-call | 20s | `InferenceClient.call(timeout=20.0)` |
| Per-pass | implicit (sum of call timeouts) | not enforced separately |
| **Per-doc wall-clock** | **30s** | `asyncio.timeout(30)` in `datalake/loop/state_machine.py` |

Per-doc is the hard outer bound — see [`02`](02-agent-loop.md).

## Client config (`datalake/config.py`)

```python
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    wafer_api_key: str
    openai_api_key: str | None = None   # only needed for eval
    judge_api_key: str                  # may equal wafer_api_key

    wafer_base_url: str = "https://api.wafer.ai/v1"
    wafer_loop_model: str = "qwen-3.5-397b"
    judge_model: str = "qwen-3.5-strong"
    openai_baseline_model: str = "gpt-4-turbo"

    wafer_concurrency: int = 64
    openai_concurrency: int = 8
    judge_concurrency: int = 4
    per_doc_concurrency: int = 8

    n_proposers: int = 3
    per_doc_budget_seconds: float = 30.0
    trace_sample_k: int = 10

    wafer_spend_ceiling_usd: float = 30.0  # hard kill switch

    class Config:
        env_file = ".env"
```

`config.yaml` overrides the defaults; environment variables override `config.yaml`.

## Hard kill switch (`datalake/inference/accounting.py`)

After every Wafer call, sum cumulative `cost_micro_usd` where `provider='wafer'` for the current `run_id`. If it exceeds `wafer_spend_ceiling_usd`:

1. Set a global `paused=True` flag.
2. All subsequent calls raise `BudgetExceededError`.
3. The orchestrator catches this and writes the current state to storage, marks remaining docs as `INGESTED` (not started), and exits cleanly.
4. Resume requires `datalake run --continue --ceiling 60` (must explicitly raise the cap).

Without this, a single misconfigured concurrency setting could exhaust the demo budget in seconds.
