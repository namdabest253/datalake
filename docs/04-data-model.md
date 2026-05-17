# 04. Data model

SQLite schema, JSONL export schema, HF dataset card layout, catalog CSV layout. Single source of truth for what gets persisted. Pass-output pydantic schemas (which map to many of these columns) live in [`03`](03-prompts-and-schemas.md).

## SQLite schema (`datalake/storage/schema.sql`)

DDL is recreated from scratch at the start of each run unless `--persist` is passed. No alembic — hackathon-pragmatic.

```sql
PRAGMA journal_mode = WAL;
PRAGMA synchronous = NORMAL;
PRAGMA foreign_keys = ON;

CREATE TABLE runs (
    id TEXT PRIMARY KEY,
    started_at REAL NOT NULL,
    ended_at REAL,
    code_commit TEXT NOT NULL,
    corpus_version TEXT NOT NULL,
    config_snapshot TEXT NOT NULL,     -- JSON, secrets redacted
    model_versions TEXT NOT NULL       -- JSON {provider:model}
);

CREATE TABLE documents (
    id TEXT PRIMARY KEY,
    run_id TEXT NOT NULL REFERENCES runs(id),
    source_path TEXT NOT NULL,
    source_hash TEXT NOT NULL,
    content_type_guess TEXT,           -- pre-loop guess from filename + first 200 chars
    ingested_at REAL NOT NULL,
    status TEXT NOT NULL,              -- INGESTED | RUNNING | DONE | FAILED
    partial INTEGER DEFAULT 0,
    timeout INTEGER DEFAULT 0,
    UNIQUE(run_id, source_hash)        -- idempotency
);
CREATE INDEX idx_documents_status ON documents(run_id, status);
CREATE INDEX idx_documents_hash ON documents(source_hash);

CREATE TABLE catalog_records (
    doc_id TEXT PRIMARY KEY REFERENCES documents(id),
    content_type TEXT NOT NULL,
    content_type_confidence REAL NOT NULL,
    ownership TEXT NOT NULL,
    ownership_confidence REAL NOT NULL,
    ownership_rationale TEXT NOT NULL,
    compliance_flags TEXT NOT NULL,    -- JSON array
    commercial_score INTEGER NOT NULL,
    commercial_action TEXT NOT NULL
);
CREATE INDEX idx_catalog_action ON catalog_records(commercial_action);
CREATE INDEX idx_catalog_score ON catalog_records(commercial_score);

CREATE TABLE label_payloads (
    doc_id TEXT PRIMARY KEY REFERENCES documents(id),
    structured_abstract TEXT NOT NULL, -- JSON
    methodology TEXT NOT NULL,         -- JSON {named:[], other_freetext:str|null}
    novelty_claim TEXT NOT NULL,
    evidence_quality TEXT NOT NULL,    -- JSON {type, strength, sample_size}
    claim_graph TEXT NOT NULL,         -- JSON
    citations TEXT NOT NULL,           -- JSON
    domain_tags TEXT NOT NULL,         -- JSON
    enriched_payload TEXT,             -- JSON (EnrichedPayload), NULL if partial
    partial INTEGER DEFAULT 0
);

CREATE TABLE trace_events (
    id TEXT PRIMARY KEY,
    doc_id TEXT NOT NULL REFERENCES documents(id),
    run_id TEXT NOT NULL REFERENCES runs(id),
    pass TEXT NOT NULL,                -- READ | PROPOSE | CRITIQUE | REFINE | VOTE | ENRICH
    proposal_idx INTEGER,              -- 0..N-1 for fan-out passes, NULL otherwise
    parent_event_id TEXT REFERENCES trace_events(id),
    started_at REAL NOT NULL,
    ended_at REAL,
    status TEXT NOT NULL,              -- OK | FAILED | TIMEOUT
    prompt_ref TEXT,                   -- JSON, inline for verbose-traced docs only
    response_ref TEXT,                 -- JSON, inline for verbose-traced docs only
    tokens_in INTEGER,
    tokens_out INTEGER,
    cost_micro_usd INTEGER             -- integer micro-dollars to avoid float drift
);
CREATE INDEX idx_trace_doc ON trace_events(doc_id, started_at);
CREATE INDEX idx_trace_pass ON trace_events(run_id, pass);

CREATE TABLE inference_calls (
    id TEXT PRIMARY KEY,
    doc_id TEXT REFERENCES documents(id),
    run_id TEXT NOT NULL REFERENCES runs(id),
    provider TEXT NOT NULL,            -- wafer | openai | judge
    model TEXT NOT NULL,
    cost_basis TEXT NOT NULL,          -- actual | estimated
    tokens_in INTEGER NOT NULL,
    tokens_out INTEGER NOT NULL,
    cost_micro_usd INTEGER NOT NULL,
    latency_ms INTEGER NOT NULL,
    status TEXT NOT NULL,              -- OK | RETRIED | FAILED
    started_at REAL NOT NULL
);
CREATE INDEX idx_inference_run_provider ON inference_calls(run_id, provider);
CREATE INDEX idx_inference_doc ON inference_calls(doc_id);

CREATE TABLE eval_pairs (
    id TEXT PRIMARY KEY,
    run_id TEXT NOT NULL REFERENCES runs(id),
    doc_id TEXT NOT NULL REFERENCES documents(id),
    datalake_record TEXT NOT NULL,    -- JSON
    gpt4_record TEXT NOT NULL,         -- JSON
    a_is_datalake INTEGER NOT NULL    -- blinding map: 1 if A=datalake, 0 if B=datalake
);

CREATE TABLE eval_results (
    pair_id TEXT PRIMARY KEY REFERENCES eval_pairs(id),
    winner TEXT NOT NULL,              -- A | B | tie
    dimension_scores TEXT NOT NULL,    -- JSON {dimension: {a:int, b:int}}
    rationale TEXT NOT NULL,
    judge_model TEXT NOT NULL,
    completed_at REAL NOT NULL
);

-- Materialized counters for dashboard O(1) reads; updated by writer task per doc completion.
CREATE TABLE dashboard_counters (
    run_id TEXT PRIMARY KEY REFERENCES runs(id),
    docs_done INTEGER DEFAULT 0,
    docs_failed INTEGER DEFAULT 0,
    docs_partial INTEGER DEFAULT 0,
    total_wafer_micro_usd INTEGER DEFAULT 0,
    total_gpt4_equivalent_micro_usd INTEGER DEFAULT 0,
    total_human_labeler_equivalent_micro_usd INTEGER DEFAULT 0,  -- per-doc Surge/Scale rate × doc count
    avg_overall_confidence REAL DEFAULT 0,
    updated_at REAL NOT NULL
);
```

## Write/read pattern

- **WAL mode mandatory.** Set on every connection (`PRAGMA journal_mode = WAL;`). Allows the dashboard process to read concurrently while the loop process writes.
- **aiosqlite.** One write connection per writer task (loop and eval each own one). Multiple read connections fine.
- **One writer task per doc.** The orchestrator owns the connection for that doc's lifetime; passes hand records back to it for persistence rather than writing themselves.
- **Cross-doc writes are serialized** by SQLite's write lock. This is the bottleneck risk: if writes ever exceed ~5k/sec, the loop will start blocking. Mitigations: trace sampling (K=10), materialized `dashboard_counters` (no aggregation queries during writes).
- **Dashboard reads** are short polls (1Hz) of pre-aggregated counter rows + small windowed queries on streams. See [`06-dashboard.md`](06-dashboard.md).

## Cost accounting

`inference_calls` is the source of truth for per-call costs. Every Wafer call gets a row with `cost_basis='actual'`. Two estimated foils are tracked for the cost-meter narrative (PRD §3):

- **GPT-4 foil** (per-call) — for every Wafer call on the main run, insert a parallel `provider='openai', cost_basis='estimated'` row with the same tokens and the GPT-4 cost computed from public pricing.
- **Human-labeler foil** (per-doc) — for every completed doc, increment `dashboard_counters.total_human_labeler_equivalent_micro_usd` by a per-content-type constant (Surge/Scale midpoint ≈ $50/paper per PRD §3). No per-call rows; a human labeler costs the same whether the loop fires 1 call or 100 per doc.

```python
GPT4_PRICING = {
    "gpt-4-turbo": {"input_per_million": 10.0, "output_per_million": 30.0},
}

def estimate_gpt4_cost(tokens_in: int, tokens_out: int) -> int:
    p = GPT4_PRICING["gpt-4-turbo"]
    usd = (tokens_in * p["input_per_million"] + tokens_out * p["output_per_million"]) / 1_000_000
    return int(usd * 1_000_000)  # micro-dollars
```

For each Wafer call on the main run, also insert a `provider='openai', cost_basis='estimated'` row with the same `tokens_in/out` but the GPT-4 cost. The dashboard cost meter sums by provider and shows both totals.

For the eval subset, GPT-4 is actually called; those rows get `cost_basis='actual'`.

## JSONL export schema (`datalake/export/jsonl.py`)

One JSON object per line, one line per document. **Custom MVP schema — not pinned to Anthropic or OpenAI fine-tune formats.** Resolves PRD §15 #4.

```json
{
  "id": "doc-uuid",
  "source_path": "corpus/arxiv/2024.12345.pdf",
  "source_hash": "sha256:...",
  "run_id": "run-uuid",
  "catalog": {
    "content_type": "research_paper",
    "content_type_confidence": 0.94,
    "ownership": "institution",
    "ownership_confidence": 0.78,
    "ownership_rationale": "Authors list university affiliation; grant funder is NSF, paper acknowledges institutional support without exclusive publisher language.",
    "compliance_flags": ["clean", "public_domain"],
    "commercial_score": 87,
    "commercial_action": "license_ready"
  },
  "label": {
    "structured_abstract": {"problem": "...", "approach": "...", "findings": "...", "limitations": "..."},
    "methodology": {"named": ["fine_tuned_bert"], "other_freetext": null},
    "novelty_claim": "First application of contrastive learning to ...",
    "evidence_quality": {"type": "empirical", "strength": "strong", "sample_size": 12000},
    "claim_graph": [{"claim": "...", "evidence_pointer": "Section 4.2, Table 3"}],
    "citations": [{"title": "...", "authors": ["..."], "year": 2022, "type": "comparison"}],
    "domain_tags": ["ml", "nlp", "information_retrieval"],
    "enriched_payload": {
      "expanded_abstract": "...",
      "novelty_rationale": "...",
      "citation_context": [],
      "claim_graph_v2": [],
      "derived_keywords": [],
      "suggested_buyer_segments": ["frontier_lab", "domain_specialist"]
    },
    "partial": false
  },
  "trace_summary": {
    "passes_completed": ["READ", "PROPOSE", "CRITIQUE", "REFINE", "VOTE", "ENRICH"],
    "vote_degraded": false,
    "timeout": false,
    "n_proposers_succeeded": 3
  },
  "costs": {
    "wafer_usd": 0.0018,
    "gpt4_equivalent_usd": 0.087,
    "human_labeler_equivalent_usd": 50.00
  },
  "model_versions": {
    "wafer_loop": "qwen-3.5-397b@2026-04",
    "judge": "qwen-3.5-strong@2026-04"
  }
}
```

## Hugging Face datasets compatibility

Loadable directly via:

```python
from datasets import load_dataset
ds = load_dataset("json", data_files="datalake_export.jsonl")
```

For explicit schema, the features dict is defined in `datalake/export/hf.py`:

```python
from datasets import Features, Value, Sequence
features = Features({
    "id": Value("string"),
    "source_path": Value("string"),
    "catalog": Features({...}),
    "label": Features({...}),
    # ...
})
```

## `dataset_card.md` auto-generation (`datalake/export/dataset_card.py`)

Template populated from SQL aggregates over the completed run:

```markdown
# Datalake dataset card

- **Run ID**: {run_id}
- **Corpus version**: {corpus_version}
- **Docs total**: {docs_done + docs_partial + docs_failed}
- **Docs done**: {docs_done} ({pct_done}%)
- **Docs partial (catalog only)**: {docs_partial}
- **Docs failed**: {docs_failed}

## Catalog distribution
- Content types: {content_type_counts}
- Ownership: {ownership_counts}
- Commercial actions: {commercial_action_counts}
- License-ready docs: {license_ready_count} ({license_ready_pct}%)

## Label quality (vs single-pass GPT-4 on 200-doc eval subset)
- Datalake win rate: {win_rate_pct}%
- Quality delta by dimension: {dimension_deltas}
- Datalake cost per doc: ${wafer_cost_per_doc}
- GPT-4 cost per doc: ${gpt4_cost_per_doc}
- Datalake / GPT-4 cost ratio: {cost_ratio}

## Models used
{model_versions table}

## Methodology
Datalake ran a 6-pass agent loop (propose × 3 → critique × 3 → refine × 3 → vote → enrich)
on Wafer Serverless. GPT-4 baseline ran single-pass with the same combined prompt.
Judge: {judge_model}, blinded A/B comparison.

GPT-4 foil cost in the dashboard cost meter is **estimated** (tokens × public pricing);
GPT-4 was only actually run on the 200-doc eval subset.
```

## Catalog CSV (`datalake/export/csv.py`)

Flat columns for the compliance team. One row per doc.

```
doc_id, source_path, content_type, content_type_confidence,
ownership, ownership_confidence, ownership_rationale,
compliance_flags, commercial_score, commercial_action
```

`compliance_flags` is pipe-delimited (e.g., `clean|public_domain`) for spreadsheet readability.

## Idempotency & migrations

- **Idempotency:** `documents.UNIQUE(run_id, source_hash)` makes re-running a corpus skip docs whose hash is already present with status `DONE`. `datalake run --retry-failed` deletes `FAILED` rows for the current run and re-queues those docs.
- **Migrations:** none. `schema.sql` is recreated each run unless `--persist`. Hackathon scope. If you want to keep data across runs, pass `--persist` and accept that DDL drift is on you.
