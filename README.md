# Datalake

**Agentic data-preparation system for universities.** Built for the Wafer "Best Inference" hackathon track.

Datalake ingests a folder of institutional documents (research papers, grant proposals) and runs a dense, multi-pass agent loop on [Wafer](https://wafer.ai) inference. Per document it produces:

- a **catalog record** — what this is, who owns it, and what compliance applies (IRB/HIPAA, FERPA, export controls, embargoes, publisher exclusivity, licensing); and
- a **rich label payload** — methodology, novelty, claims, evidence, and citations, ready for an AI lab to train on.

The bet: a cheap, fast ensemble loop produces higher-quality labels than a single pass of an expensive frontier model — at a fraction of the cost. Datalake proves it with a live, non-mocked side-by-side eval against a single-pass GPT-4 baseline.

## How it works

```
ingest/  ──▶  loop/ (asyncio)  ──▶  storage/        ──▶  export/
PDF+ZIP       propose → critique     SQLite (WAL)         JSONL + CSV + dataset_card
parser        → refine → vote                │
              → enrich                        ├──▶  dashboard/  (Streamlit, 6 live panels)
                  │                           └──▶  api/        (JSON HTTP → React frontend)
                  ▼
              inference/  (Wafer · OpenAI baseline · Judge)
                  │
                  ▼
              eval/  (side-by-side vs single-pass GPT-4)
```

Everything is a single Python process on a single asyncio event loop — no workers, queues, or external services. SQLite (WAL mode) is the single source of truth; the dashboard, API, and eval all read from it. See [`docs/01-architecture.md`](docs/01-architecture.md).

### The agent loop (per document)

| Pass | What it does |
|---|---|
| **propose** | `N=3` parallel proposer agents each draft a full record |
| **critique** | one critic per proposal finds weaknesses |
| **refine** | each proposal is revised against its critique |
| **vote** | a voter picks the strongest refined proposal |
| **enrich** | adds the label payload (methodology, novelty, claims) |

Every pass output is validated against a pydantic schema; failures are repaired-and-retried, and a doc that can't fully complete is flagged `partial=true` rather than dropped. See [`docs/02-agent-loop.md`](docs/02-agent-loop.md).

## Quick start

Requires Python 3.11+ and [`uv`](https://github.com/astral-sh/uv).

```bash
# 1. Install (creates .venv, installs all extras)
make install               # == uv sync --all-extras

# 2. Configure secrets
cp .env.example .env        # then fill in WAFER_API_KEY (and OPENAI_API_KEY for eval)

# 3. Run the pipeline
uv run datalake ingest demo_corpus/synthetic/   # parse + insert documents
uv run datalake run                             # run the 6-pass loop
uv run datalake eval --n 10                     # side-by-side vs GPT-4 baseline
uv run datalake export                          # emit JSONL + CSV + dataset card

# 4. See it live (pick one UI)
uv run datalake dashboard                       # Streamlit, http://localhost:8501
uv run datalake api                             # JSON API for the React frontend
```

Or run the whole demo path at once: `make demo`.

### CLI commands

| Command | Purpose |
|---|---|
| `datalake ingest <path>` | Walk a folder, parse PDFs/text/JSON, insert `documents` rows |
| `datalake run` | Run the 6-pass loop on ingested docs (defaults to the most recent run) |
| `datalake eval --n 200` | Side-by-side Datalake vs single-pass baseline, writes a JSON report |
| `datalake export` | Emit `<run>.jsonl`, `<run>-catalog.csv`, `<run>-dataset_card.md` |
| `datalake dashboard` | Launch the Streamlit UI (`--port`, default 8501) |
| `datalake api` | Launch the JSON HTTP API backing `frontend/` (`--port`, default 8000) |

Run any command with `--help` for its full flag list (e.g. `--limit`, `--ceiling`, `--run-id`, `--dry-run`).

## Frontend (React)

The Streamlit dashboard is the demo-grade UI; `frontend/` is a richer React + Vite + Tailwind app that talks to `datalake api`.

```bash
uv run datalake api               # terminal 1 — API on http://localhost:8000
cd frontend && npm install && npm run dev   # terminal 2 — http://localhost:5173
```

The API base URL defaults to `http://localhost:8000`; override it with `VITE_API_BASE` in `frontend/.env.local`. Endpoints include `/api/health`, `/api/counters`, `/api/catalog`, `/api/stream`, `/api/runs`, `/api/eval/pair`, and `/api/export/download`.

## Configuration

- **`.env`** — secrets and deployment values (`WAFER_API_KEY`, `WAFER_BASE_URL`, model names, `OPENAI_API_KEY`, `JUDGE_API_KEY`). See [`.env.example`](.env.example).
- **`config.yaml`** — tuning knobs: concurrency caps, `n_proposers`, per-doc budget, trace sampling, and the `wafer_spend_ceiling_usd` hard kill switch.

Precedence: CLI flags override environment variables override `config.yaml`. Loaded via `pydantic-settings`.

> **Note on eval cost:** the "GPT-4 baseline" column makes no real OpenAI calls by default — it runs a single-pass call against the same Wafer family, and the GPT-4 dollar figure is *estimated* from token counts × published GPT-4 rates. See [`docs/07-evaluation.md`](docs/07-evaluation.md).

## Development

```bash
make test     # uv run pytest -x
make smoke    # integration tests only (golden 5-doc run)
make lint     # ruff check + format --check
make format   # ruff format + autofix
make clean    # remove .datalake/, caches, __pycache__
```

## Project layout

```
datalake/        Python package (cli, config, ingest, loop, prompts,
                 inference, storage, eval, export, dashboard, api)
frontend/        React + Vite + Tailwind UI (talks to `datalake api`)
demo_corpus/     Synthetic documents incl. planted compliance edge cases
docs/            Implementation spec (start at docs/00-overview.md)
scripts/         Corpus seeding + edge-case planting
tests/           unit / integration / fixtures
PRD.md           Product reasoning and pitch
config.yaml      Runtime tuning knobs
```

## Scope

This is a demo-quality MVP, deliberately **not** a production system. Out of scope: real institutional connectors (S3, SharePoint, DSpace), production compliance certification, auth/multi-tenancy, durable queues or multi-process workers, and human-in-the-loop review. Compliance labels are heuristic with confidence scores, not legal determinations.
