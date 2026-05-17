"""Per-pass pydantic schemas + prompt template builders.

The schemas are the authoritative wire format for every pass output —
the model must return JSON matching them, and pydantic validates on receipt.
See docs/03-prompts-and-schemas.md §JSON schemas and §Prompt templates.
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

from datalake.prompts.taxonomies import (
    METHODOLOGY_NAMED,
    CommercialAction,
    ComplianceFlag,
    ContentType,
    Ownership,
)


# ---------------------------------------------------------------------------
# Schemas
# ---------------------------------------------------------------------------


class CatalogFields(BaseModel):
    content_type: ContentType
    content_type_confidence: float = Field(ge=0, le=1)
    ownership: Ownership
    ownership_confidence: float = Field(ge=0, le=1)
    ownership_rationale: str = Field(max_length=300)
    compliance_flags: list[ComplianceFlag]
    commercial_score: int = Field(ge=0, le=100)
    commercial_action: CommercialAction


class LabelFields(BaseModel):
    structured_abstract: dict[Literal["problem", "approach", "findings", "limitations"], str]
    methodology_named: list[str]  # subset of METHODOLOGY_NAMED
    methodology_other_freetext: str | None = None
    novelty_claim: str = Field(max_length=500)
    evidence_type: Literal["empirical", "theoretical", "simulation", "survey", "mixed"]
    evidence_strength: Literal["weak", "moderate", "strong"]
    sample_size: int | None = None
    claim_graph: list[dict]  # [{claim:str, evidence_pointer:str}]
    citations: list[dict]  # [{title, authors, year, type}]
    domain_tags: list[str]


class ProposalRecord(BaseModel):
    catalog: CatalogFields
    label: LabelFields
    overall_confidence: float = Field(ge=0, le=1)


class FieldCritique(BaseModel):
    field_path: str
    issue: Literal["too_vague", "wrong", "missing_evidence", "contradicted_by_source", "ok"]
    suggestion: str | None = None


class Critique(BaseModel):
    proposal_idx: int
    field_critiques: list[FieldCritique]
    overall_assessment: Literal["accept", "revise", "reject"]
    rationale: str = Field(max_length=300)


class RefinedRecord(ProposalRecord):
    revision_summary: str = Field(max_length=300)


class VoteResult(BaseModel):
    winner_idx: int
    winner_confidence: float = Field(ge=0, le=1)
    rationale: str = Field(max_length=300)
    runners_up: list[int] = Field(default_factory=list)


class EnrichedPayload(BaseModel):
    expanded_abstract: str = Field(max_length=2000)
    novelty_rationale: str = Field(max_length=800)
    citation_context: list[dict]
    claim_graph_v2: list[dict]
    derived_keywords: list[str]
    suggested_buyer_segments: list[
        Literal["frontier_lab", "domain_specialist", "data_marketplace", "academic_archive"]
    ]


# ---------------------------------------------------------------------------
# Prompt template builders
# ---------------------------------------------------------------------------

# Shared system message preamble. Taxonomies + heuristics are injected at build time.
SYSTEM_PREAMBLE = """\
You are a {role} for Datalake, a university data-preparation system.

Taxonomies you MUST use (do not invent values):
  content_type:       {content_types}
  ownership:          {ownerships}
  compliance_flags:   {compliance_flags}
  commercial_action:  {commercial_actions}
  methodology_named:  {methodology_named}

Compliance heuristics:
{heuristics}

Respond with valid JSON matching the provided schema. No prose."""


def build_system(role: str, heuristics_yaml: str) -> str:
    """Render the shared system preamble with taxonomies and heuristics injected."""
    return SYSTEM_PREAMBLE.format(
        role=role,
        content_types=[e.value for e in ContentType],
        ownerships=[e.value for e in Ownership],
        compliance_flags=[e.value for e in ComplianceFlag],
        commercial_actions=[e.value for e in CommercialAction],
        methodology_named=METHODOLOGY_NAMED,
        heuristics=heuristics_yaml,
    )


def build_propose_user(document_text: str, references: list[dict], content_type_guess: str) -> str:
    """User message for the PROPOSE pass. See docs/03 §PROPOSE prompt."""
    raise NotImplementedError("TODO: render the PROPOSE template with truncated doc text")


def build_critique_user(proposal: ProposalRecord, document_text: str, idx: int, n: int) -> str:
    """User message for the CRITIQUE pass. See docs/03 §CRITIQUE prompt."""
    raise NotImplementedError("TODO: render the CRITIQUE template")


def build_refine_user(proposal: ProposalRecord, critique: Critique, document_text: str) -> str:
    """User message for the REFINE pass. See docs/03 §REFINE prompt."""
    raise NotImplementedError("TODO: render the REFINE template")


def build_vote_user(refined: list[RefinedRecord], document_text: str) -> str:
    """User message for the VOTE pass. See docs/03 §VOTE prompt."""
    raise NotImplementedError("TODO: render the VOTE template")


def build_enrich_user(winning_refined: RefinedRecord, document_text: str) -> str:
    """User message for the ENRICH pass. See docs/03 §ENRICH prompt."""
    raise NotImplementedError("TODO: render the ENRICH template")


# Token budgets per pass — drives truncation and the cost meter.
# See docs/03-prompts-and-schemas.md §Token budgets.
TOKEN_BUDGETS = {
    "propose": {"input_cap": 6000, "output_cap": 1500},
    "critique": {"input_cap": 4000, "output_cap": 800},
    "refine": {"input_cap": 5000, "output_cap": 1500},
    "vote": {"input_cap": 3000, "output_cap": 300},
    "enrich": {"input_cap": 8000, "output_cap": 2500},
    "judge": {"input_cap": 6000, "output_cap": 700},
}

# Temperature per pass — see docs/02-agent-loop.md §Determinism knobs.
PASS_TEMPERATURE = {
    "propose": 0.8,
    "critique": 0.4,
    "refine": 0.2,
    "vote": 0.0,
    "enrich": 0.5,
    "judge": 0.0,
}
