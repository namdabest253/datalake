-- LakeAudit SQLite schema.
-- Recreated from scratch each run unless --persist is passed.
-- See docs/04-data-model.md §SQLite schema.

PRAGMA journal_mode = WAL;
PRAGMA synchronous = NORMAL;
PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS runs (
    id TEXT PRIMARY KEY,
    started_at REAL NOT NULL,
    ended_at REAL,
    code_commit TEXT NOT NULL,
    corpus_version TEXT NOT NULL,
    config_snapshot TEXT NOT NULL,     -- JSON, secrets redacted
    model_versions TEXT NOT NULL       -- JSON {provider:model}
);

CREATE TABLE IF NOT EXISTS documents (
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
CREATE INDEX IF NOT EXISTS idx_documents_status ON documents(run_id, status);
CREATE INDEX IF NOT EXISTS idx_documents_hash ON documents(source_hash);

CREATE TABLE IF NOT EXISTS catalog_records (
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
CREATE INDEX IF NOT EXISTS idx_catalog_action ON catalog_records(commercial_action);
CREATE INDEX IF NOT EXISTS idx_catalog_score ON catalog_records(commercial_score);

CREATE TABLE IF NOT EXISTS label_payloads (
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

CREATE TABLE IF NOT EXISTS trace_events (
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
CREATE INDEX IF NOT EXISTS idx_trace_doc ON trace_events(doc_id, started_at);
CREATE INDEX IF NOT EXISTS idx_trace_pass ON trace_events(run_id, pass);

CREATE TABLE IF NOT EXISTS inference_calls (
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
CREATE INDEX IF NOT EXISTS idx_inference_run_provider ON inference_calls(run_id, provider);
CREATE INDEX IF NOT EXISTS idx_inference_doc ON inference_calls(doc_id);

CREATE TABLE IF NOT EXISTS eval_pairs (
    id TEXT PRIMARY KEY,
    run_id TEXT NOT NULL REFERENCES runs(id),
    doc_id TEXT NOT NULL REFERENCES documents(id),
    lakeaudit_record TEXT NOT NULL,    -- JSON
    gpt4_record TEXT NOT NULL,         -- JSON
    a_is_lakeaudit INTEGER NOT NULL    -- blinding map: 1 if A=lakeaudit, 0 if B=lakeaudit
);

CREATE TABLE IF NOT EXISTS eval_results (
    pair_id TEXT PRIMARY KEY REFERENCES eval_pairs(id),
    winner TEXT NOT NULL,              -- A | B | tie
    dimension_scores TEXT NOT NULL,    -- JSON {dimension: {a:int, b:int}}
    rationale TEXT NOT NULL,
    judge_model TEXT NOT NULL,
    completed_at REAL NOT NULL
);

-- Materialized counters for dashboard O(1) reads.
-- Updated by writer task per doc completion (see docs/06-dashboard.md §Materialized counters).
CREATE TABLE IF NOT EXISTS dashboard_counters (
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
