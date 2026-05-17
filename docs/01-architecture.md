# 01. Architecture

System shape, module layout, process model, tech stack. The detailed contracts for each subsystem live in their own files; this is the orientation map.

## System diagram

```
┌──────────────┐   ┌──────────────────────────────────────┐   ┌────────────┐
│  ingest/     │──▶│  loop/ (asyncio task group)          │──▶│  storage/  │
│  PDF + ZIP   │   │  propose → critique → refine →       │   │  SQLite    │
│  parser      │   │  vote → enrich   (per doc)           │   │  (WAL)     │
└──────────────┘   └──────────────────────────────────────┘   └─────┬──────┘
                                  │                                  │
                                  ▼                                  ▼
                          ┌──────────────┐                  ┌─────────────────┐
                          │  inference/  │                  │  export/        │
                          │  Wafer +     │                  │  JSONL + CSV +  │
                          │  OpenAI +    │                  │  dataset_card   │
                          │  Judge       │                  └─────────────────┘
                          └──────────────┘                          │
                                                                    ▼
                          ┌──────────────┐                  ┌─────────────────┐
                          │  eval/       │◀─────reads───────│  dashboard/     │
                          │  harness +   │                  │  Streamlit      │
                          │  scoring     │─────writes──────▶│  6 panels       │
                          └──────────────┘    eval_results  └─────────────────┘
```

All arrows are in-process (no IPC). Storage is the single source of truth; dashboard and eval both read from SQLite.

## Module layout

```
lakeaudit/
  __init__.py
  cli.py                  # Typer/argparse — ingest, run, eval, export, dashboard subcommands
  config.py               # pydantic-settings — loads .env and config.yaml
  ingest/
    parser.py             # PyMuPDF wrapper, text + reference extraction
    queue.py              # asyncio.Queue feeder for the loop
  loop/
    state_machine.py      # 6-pass orchestrator, task group, partial-failure policy
    passes/
      propose.py
      critique.py
      refine.py
      vote.py
      enrich.py
  prompts/
    templates.py          # Per-pass prompt builders (system + user msgs)
    taxonomies.py         # Content type, ownership, compliance, methodology enums
    heuristics.yaml       # Compliance heuristics, demoable on stage
  inference/
    base.py               # InferenceClient protocol + shared wrappers
    wafer.py              # Wafer Serverless client
    openai.py             # GPT-4 baseline + estimated foil cost
    judge.py              # Wafer-hosted stronger model for eval
    retry.py              # Exponential backoff + JSON repair retry
    accounting.py         # Token + cost tracking, hard kill switch
  storage/
    schema.sql            # All DDL
    db.py                 # aiosqlite connection pool, WAL mode
    models.py             # pydantic models that map to SQLite tables
  eval/
    harness.py            # Runs 200-doc subset through both pipelines in parallel
    judge_runner.py       # Calls judge on each pair with blinded A/B
    scoring.py            # Win rate, quality delta math
  export/
    jsonl.py              # JSONL writer matching the export schema in 04
    hf.py                 # Hugging Face datasets features dict
    csv.py                # Catalog CSV for compliance team
    dataset_card.py       # Auto-generated dataset card from SQL aggregates
  dashboard/
    app.py                # Streamlit entrypoint, 6 panels
    panels/               # One file per panel
    queries.py            # Verbatim SQL used by panels
tests/
  unit/                   # Schema validation, state machine with mocked client
  integration/            # Golden 5-doc test
  fixtures/               # Sample PDFs, canned API responses, judge pairs
scripts/
  seed_corpus.py          # Downloads arXiv/NSF subset
  plant_edge_cases.py     # Adds the ~30 synthetic compliance cases
docs/                     # This tree
```

## Process model

Single Python process. Single asyncio event loop. No workers, no celery, no redis, no kafka. The agent loop runs N docs in parallel with bounded concurrency; the dashboard runs as a separate `streamlit run dashboard/app.py` process that reads SQLite.

Two processes total during a demo:

1. `lakeaudit run` (the loop)
2. `streamlit run lakeaudit/dashboard/app.py` (the UI)

Both can run on the same machine, communicating only through SQLite (WAL mode allows concurrent reads with the writer).

## Tech stack

| Component | Choice | Why |
|---|---|---|
| Language | Python 3.11+ | asyncio task groups, exception groups, structural pattern matching |
| Concurrency | `asyncio` + `aiohttp` | Single event loop, no threading; aiohttp for non-blocking HTTP |
| DB | SQLite + `aiosqlite` (WAL mode) | Zero-config, file-based, supports concurrent reads with one writer |
| PDF parsing | PyMuPDF (`pymupdf`) | Fast, robust text + reference extraction |
| Validation | pydantic v2 | JSON schema enforcement on every pass output; settings management |
| Config | pydantic-settings | `.env` for keys, `config.yaml` for tunables |
| Logging | loguru | Structured JSON logs, zero-config |
| Token counting | `tiktoken` | Local cost estimation before API response arrives |
| Frontend | Streamlit + `streamlit-autorefresh` | Demo-grade UI in tens of lines per panel |
| Env mgmt | `uv` | Fast install, deterministic locks |
| Inference (loop) | Wafer Serverless (Qwen3.5-397B) | The loop; cheap fast inference is the product thesis |
| Baseline | OpenAI GPT-4 | Eval-subset only, ~200 docs; never on the main run |
| Judge | Wafer-hosted stronger model | Resolves PRD §15 #1 — "Wafer-only is a better sponsor story" |

## Component contracts (high-level)

Detailed schemas live in [`04`](04-data-model.md). This is the producer/consumer map.

| Module | Produces | Consumes |
|---|---|---|
| `ingest/` | `documents` rows + extracted text in memory | Folder of files |
| `loop/` | `catalog_records`, `label_payloads`, `trace_events`, `inference_calls` | `documents` text |
| `inference/` | Provider-agnostic call results + cost rows | Pass-specific prompts |
| `storage/` | Read API for dashboard/export; write API for loop/eval | SQL queries |
| `eval/` | `eval_pairs`, `eval_results` | Held-out doc subset + both pipeline outputs |
| `export/` | JSONL, CSV, `dataset_card.md` | All storage tables |
| `dashboard/` | UI | Read-only queries against storage |

## Concurrency topology

```
                 ┌────────────────────────────────────────┐
                 │  Global doc-level semaphore (N=8)      │
                 │  ──── controls how many docs run in    │
                 │       parallel through the loop        │
                 └────────────────────────────────────────┘
                                     │
                                     ▼ (per doc)
        ┌─────────────────────────────────────────────────────────┐
        │  Per-doc task group with 30s wall-clock budget          │
        │                                                         │
        │  PROPOSE_FANOUT (3 parallel calls)                      │
        │      └── each gated by per-doc inner semaphore (=8)     │
        │  CRITIQUE_FANOUT (3 parallel calls, one per proposal)   │
        │  REFINE (3 parallel calls)                              │
        │  VOTE (1 call)                                          │
        │  ENRICH (1 call)                                        │
        │                                                         │
        │  All calls also gated by global provider semaphores:    │
        │  WAFER_CONCURRENCY=64, OPENAI=8, JUDGE=4                │
        └─────────────────────────────────────────────────────────┘
```

Numeric defaults live in [`05-inference-client.md`](05-inference-client.md). Topology shape lives here.

## Reproducibility

Every record carries a `run_id`. Each run captures:

- `corpus_version` (hash of the input folder structure)
- `code_commit` (git SHA at startup)
- `model_versions` (provider + model name + revision per pass)
- `config_snapshot` (full resolved `config.yaml` + env values, secrets redacted)

Without this, side-by-side comparisons across runs are invalid (e.g., if Wafer's model rev silently changes between dry runs and the demo).

## Out of scope (call out explicitly so scope creep dies fast)

- Real institutional connectors (S3, SharePoint, DSpace, Fedora, Box)
- Authentication, multi-tenancy, multi-user
- Durable message queue, retries with DLQ, persistent task state
- Multi-process workers (celery, redis, kafka)
- Production compliance certification or legal review workflows
- Marketplace integration (Kled, HF Hub publishing)
- Human-in-the-loop active learning
- Domain coverage beyond research papers + grant proposals
- Live SaaS deployment (the demo is local)
