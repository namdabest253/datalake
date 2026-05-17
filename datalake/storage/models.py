"""Pydantic models that map to SQLite tables.

These are the row-level shapes used by the storage layer. They differ from the
pass-output schemas in datalake/prompts/templates.py (those are the *wire format*
between the loop and the inference provider; this is the *persisted format*).

See docs/04-data-model.md §SQLite schema.
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field


class Run(BaseModel):
    id: str
    started_at: float
    ended_at: float | None = None
    code_commit: str
    corpus_version: str
    config_snapshot: str  # JSON, secrets redacted
    model_versions: str  # JSON {provider: model}


class Document(BaseModel):
    id: str
    run_id: str
    source_path: str
    source_hash: str
    content_type_guess: str | None = None
    ingested_at: float
    status: Literal["INGESTED", "RUNNING", "DONE", "FAILED"]
    partial: bool = False
    timeout: bool = False
    # In-memory only — populated by the parser, not persisted in the documents row.
    text: str | None = None
    references: list[dict] = Field(default_factory=list)


class CatalogRecord(BaseModel):
    doc_id: str
    content_type: str
    content_type_confidence: float
    ownership: str
    ownership_confidence: float
    ownership_rationale: str
    compliance_flags: list[str]
    commercial_score: int
    commercial_action: str


class LabelPayload(BaseModel):
    doc_id: str
    structured_abstract: dict
    methodology: dict  # {named: [], other_freetext: str | None}
    novelty_claim: str
    evidence_quality: dict
    claim_graph: list[dict]
    citations: list[dict]
    domain_tags: list[str]
    enriched_payload: dict | None = None
    partial: bool = False


class TraceEvent(BaseModel):
    id: str
    doc_id: str
    run_id: str
    pass_: str = Field(alias="pass")
    proposal_idx: int | None = None
    parent_event_id: str | None = None
    started_at: float
    ended_at: float | None = None
    status: Literal["OK", "FAILED", "TIMEOUT"]
    prompt_ref: dict | None = None
    response_ref: dict | None = None
    tokens_in: int | None = None
    tokens_out: int | None = None
    cost_micro_usd: int | None = None


class InferenceCall(BaseModel):
    id: str
    doc_id: str | None = None
    run_id: str
    provider: Literal["wafer", "openai", "judge"]
    model: str
    cost_basis: Literal["actual", "estimated"]
    tokens_in: int
    tokens_out: int
    cost_micro_usd: int
    latency_ms: int
    status: Literal["OK", "RETRIED", "FAILED"]
    started_at: float


class EvalPair(BaseModel):
    id: str
    run_id: str
    doc_id: str
    datalake_record: dict
    gpt4_record: dict
    a_is_datalake: bool


class EvalResult(BaseModel):
    pair_id: str
    winner: Literal["A", "B", "tie"]
    dimension_scores: dict
    rationale: str
    judge_model: str
    completed_at: float


class DashboardCounters(BaseModel):
    run_id: str
    docs_done: int = 0
    docs_failed: int = 0
    docs_partial: int = 0
    total_wafer_micro_usd: int = 0
    total_gpt4_equivalent_micro_usd: int = 0
    total_human_labeler_equivalent_micro_usd: int = 0
    avg_overall_confidence: float = 0.0
    updated_at: float
