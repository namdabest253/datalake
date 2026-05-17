# 08. Ops and demo

CLI, config, observability, testing, demo runbook, failure modes.

## CLI entrypoints (`lakeaudit/cli.py`)

```
lakeaudit ingest <path> [--run-id <id>] [--persist]
  Walk a folder, parse PDFs, insert documents rows. Does not run the loop.

lakeaudit run [--run-id <id>] [--persist] [--continue] [--retry-failed]
              [--ceiling <usd>] [--debug] [--sample-rate <k>]
  Run the agent loop on all INGESTED docs for this run.

lakeaudit eval --n <count> [--run-id <id>] [--dry-run] [--judge-model <name>]
  Run the 200-doc side-by-side eval. GPT-4 actually executes here.

lakeaudit export [--run-id <id>] [--out <dir>]
  Emit JSONL + CSV + dataset_card.md + HF features dict.

lakeaudit dashboard [--run-id <id>] [--port 8501]
  Launch the Streamlit UI. (Wraps `streamlit run lakeaudit/dashboard/app.py`.)
```

All commands accept `--config <path>` to override the default `config.yaml`. All log to stderr in structured JSON via loguru; `--debug` switches to colorized human-readable.

## Config & secrets

`.env` (gitignored; `.env.example` checked in):

```
WAFER_API_KEY=wfr_...
OPENAI_API_KEY=sk-...       # only needed for eval
JUDGE_API_KEY=wfr_...       # often same as WAFER_API_KEY
```

`config.yaml` (checked in, has defaults):

```yaml
wafer_base_url: https://api.wafer.ai/v1
wafer_loop_model: qwen-3.5-397b
judge_model: qwen-3.5-strong
openai_baseline_model: gpt-4-turbo

wafer_concurrency: 64
openai_concurrency: 8
judge_concurrency: 4
per_doc_concurrency: 8

n_proposers: 3
per_doc_budget_seconds: 30
trace_sample_k: 10

wafer_spend_ceiling_usd: 30

paths:
  sqlite_db: ./.lakeaudit/lakeaudit.db
  logs_dir: ./.lakeaudit/logs
  heuristics: ./lakeaudit/prompts/heuristics.yaml
  judge_rubric: ./lakeaudit/eval/judge_rubric.yaml
```

Loaded via pydantic-settings; env vars override `config.yaml`; CLI flags override env.

## Local-dev setup

```
uv sync
cp .env.example .env       # fill in keys
make demo                  # ingest sample corpus + run + eval + dashboard
```

`Makefile` targets:

```
demo:    seed sample → ingest → run --n 50 → eval --n 10 → dashboard
smoke:   golden 5-doc integration test (mocked InferenceClient)
test:    pytest -x
lint:    ruff check + ruff format --check
```

SQLite path defaults to `./.lakeaudit/lakeaudit.db`. Wipe with `rm -rf .lakeaudit/`.

## Observability

- **Logs**: loguru, structured JSON to stderr (or `./.lakeaudit/logs/run_<run_id>.log` for persistent runs). `--debug` flag flips to human-readable + DEBUG level.
- **Trace events**: `trace_events` table is the system of record for the loop. Every state transition writes a row. Verbose-traced docs (K=10) include full prompts and responses.
- **Cost ledger**: `inference_calls` table is the system of record for cost. Both Wafer-actual and GPT-4-estimated rows.
- **No external APM** (no Sentry, no Datadog). Hackathon scope.

## Testing strategy

- **Unit (`tests/unit/`)**
  - Pydantic schemas validate against canned API responses in `tests/fixtures/api_responses/`.
  - State machine driven with a `MockInferenceClient` that returns deterministic results.
  - Cost accounting math (rounding, GPT-4 estimation).
- **Integration (`tests/integration/`)**
  - Golden end-to-end test on 5 fixture PDFs in `tests/fixtures/corpus/`.
  - Uses `MockInferenceClient` — no live Wafer or OpenAI calls in CI.
  - Asserts: 5 catalog records + 5 label payloads + ~55 trace events written; JSONL export matches fixture.
  - Runtime <30s.
- **Smoke (`make smoke`)**
  - Same as integration, runnable manually for pre-demo confidence.
- **Eval self-test** (see [`07`](07-evaluation.md))
  - Judge model called on a canonical pair before each `lakeaudit eval` invocation.

## Demo runbook

**Pre-demo (T-24h):**

1. `make smoke` — green.
2. `lakeaudit ingest demo_corpus/bulk/` — 20k docs, takes ~10 min.
3. `lakeaudit run --run-id demo` — full bulk processing, takes ~30 min, caches results.
4. `lakeaudit eval --n 200 --run-id demo` — populates `eval_results`.
5. Verify dashboard renders all 6 panels with non-empty data.
6. Verify `wafer_spend_ceiling_usd` is set higher than the actual spend (it shouldn't trip during demo).
7. Pre-recorded fallback video saved to `demo_assets/fallback.mp4`.

**Live demo (T-0):**

1. `streamlit run lakeaudit/dashboard/app.py` — opens to populated dashboard (bulk results visible).
2. Open a separate terminal: `lakeaudit ingest demo_corpus/live_slice/` (50 held-back docs).
3. Run: `lakeaudit run --run-id demo` (resumes; processes the 50 new docs live).
4. Switch to dashboard — watch document stream + loop visualizer + cost meter update live.
5. **Heuristic edit moment**: open `lakeaudit/prompts/heuristics.yaml` in front of judges, add a new rule (e.g., "if document mentions 'preprint' and 'medRxiv', flag as `clean`"), save.
6. Re-run: `lakeaudit run --run-id demo --retry-failed` on the slice that triggers the new rule.
7. Show the updated catalog filter view — license-ready count moves.
8. Click through eval panel — show win rate, per-dimension deltas, cost ratio.

## Likely judge questions (and one-line answers)

Drawn primarily from PRD §3 (competitive landscape). Have these ready and rehearsed; they're the questions most likely to land.

| Question | Short answer |
|---|---|
| "Why not just use Scale AI for the labeling?" | At $30–$60/paper Surge-tier rates the seller's margin is zero — Scale's cost structure is structurally locked out of this market. Wafer at fractions of a cent is the only price point that works. |
| "Why catalog + label as one product, not two?" | Five reasons (PRD §3): end-to-end economics, shared inference compounds across passes, vendor-handoff friction is what froze the market, compliance signal must ride with labels, catalog-alone is consulting not infrastructure. |
| "Aren't these just AI-generated labels (low quality)?" | Side-by-side eval panel: ≥65% win rate vs single-pass GPT-4, scored by an independent judge model on six dimensions. Click into the panel. |
| "Why universities and not generic labeling?" | Universities are the only market where catalog + label converge into one workflow with one buyer type (AI labs licensing rights-clean training data). Generic labeling is crowded; institutional data prep is empty. |
| "How does this scale beyond R1 research?" | Same architecture applies to hospital systems (medical research), museums (archival material), research labs. Future scope per PRD §14, not MVP. |
| "What about the legal liability of acting on these compliance labels?" | MVP labels are heuristic with confidence scores — designed to inform legal review, not replace it. Production-grade certification is explicitly out of scope (PRD §4). |
| "Could a frontier-lab in-house team just build this?" | They could but they won't — their product is the model, not the seller-side data infrastructure. Their buyer-side pipelines already assume pre-cleared data, which is the assumption that fails at universities. |

## Failure modes & fallbacks

| Failure | Detection | Fallback |
|---|---|---|
| Wafer rate-limited mid-demo | 429 storm in logs; loop visualizer stalls | Loop has cached bulk results; dashboard still renders. Switch narrative to filter/eval panels. |
| Network down | aiohttp connect errors | Pre-recorded `demo_assets/fallback.mp4` |
| Wafer cluster red | 5xx storm | `lakeaudit run --offline` mode replays a cached run from `demo_assets/replay.jsonl` into a fresh SQLite |
| Hard kill switch trips | `BudgetExceededError` in logs | Raise `--ceiling 60` and re-run; budget was misconfigured |
| Streamlit crashes | Empty browser tab | `streamlit run` again; reads same SQLite, picks up state |
| Pre-recorded video bombs | Can't play locally | mp4 also uploaded to a private YouTube unlisted URL; QR code on the laptop screen |

## Pre-demo checklist

```
[ ] Keys valid (WAFER_API_KEY, OPENAI_API_KEY, JUDGE_API_KEY)
[ ] config.yaml committed with demo settings (n_proposers=3, ceiling=30)
[ ] make smoke green
[ ] Bulk corpus pre-processed; SQLite contains ~20k DONE docs
[ ] eval_results populated for ≥200 pairs
[ ] Win rate ≥65% on eval (or note the gap and prepare to address)
[ ] Cost ratio ≤30% on eval
[ ] Dashboard renders all 6 panels without empty states
[ ] Foil methodology annotation visible on cost meter panel
[ ] Live slice (50 docs) held back, not yet processed
[ ] Heuristics demo: rule prepared to add live
[ ] Pre-recorded fallback video tested
[ ] Laptop battery + charger; ethernet adapter if Wi-Fi flaky
```

## Data license notes

- **arXiv papers**: covered by arXiv's terms of use; metadata is openly licensed. Full-text reuse for non-commercial analysis is permitted. The demo corpus is downloaded once, stored locally under `demo_corpus/arxiv/`, not redistributed.
- **NSF grant abstracts**: public domain (federal government works). Stored under `demo_corpus/nsf/`.
- **Planted edge cases**: ~30 synthetic documents hand-authored to exercise compliance heuristics. Stored under `demo_corpus/synthetic/` with prominent `SYNTHETIC` filename prefix. **Disclosed in the demo narrative** to head off "is this real institutional data?" mid-presentation.
