"""Per-pass pydantic schemas + prompt template builders.

The schemas are the authoritative wire format for every pass output —
the model must return JSON matching them, and pydantic validates on receipt.
See docs/03-prompts-and-schemas.md §JSON schemas and §Prompt templates.
"""

from __future__ import annotations

import json
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
    ownership_rationale: str = Field(max_length=800)
    compliance_flags: list[ComplianceFlag]
    commercial_score: int = Field(ge=0, le=100)
    commercial_action: CommercialAction


class LabelFields(BaseModel):
    structured_abstract: dict[Literal["problem", "approach", "findings", "limitations"], str]
    methodology_named: list[str]  # subset of METHODOLOGY_NAMED
    methodology_other_freetext: str | None = None
    novelty_claim: str = Field(max_length=1200)
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
    # Model sometimes returns a list of suggestions or even structured values; accept anything
    # JSON-serializable and store as-is so we don't reject otherwise-useful critiques.
    suggestion: str | list | dict | None = None


class Critique(BaseModel):
    proposal_idx: int
    field_critiques: list[FieldCritique]
    overall_assessment: Literal["accept", "revise", "reject"]
    rationale: str = Field(max_length=1000)


class RefinedRecord(ProposalRecord):
    revision_summary: str = Field(max_length=1000)


class VoteResult(BaseModel):
    winner_idx: int
    winner_confidence: float = Field(ge=0, le=1)
    rationale: str = Field(max_length=1000)
    runners_up: list[int] = Field(default_factory=list)


class EnrichedPayload(BaseModel):
    expanded_abstract: str = Field(max_length=4000)
    novelty_rationale: str = Field(max_length=1500)
    citation_context: list[dict]
    claim_graph_v2: list[dict]
    derived_keywords: list[str]
    suggested_buyer_segments: list[
        Literal["frontier_lab", "domain_specialist", "data_marketplace", "academic_archive"]
    ]


class DimensionScore(BaseModel):
    """Per-record dimension scores from the eval judge. See docs/07-evaluation.md."""

    methodology_specificity: int = Field(ge=1, le=5)
    novelty_claim_accuracy: int = Field(ge=1, le=5)
    evidence_quality: int = Field(ge=1, le=5)
    citation_completeness: int = Field(ge=1, le=5)
    compliance_correctness: int = Field(ge=1, le=5)
    ownership_defensibility: int = Field(ge=1, le=5)


class JudgeOutput(BaseModel):
    """Output of one judge call comparing record_a vs record_b. Blinded — judge does
    not know which is Datalake. See docs/07-evaluation.md §Blinding."""

    winner: Literal["A", "B", "tie"]
    a_scores: DimensionScore
    b_scores: DimensionScore
    # 2500 not 1000 — Qwen judges naturally produce per-dimension justifications
    # that add up to ~1500–2000 chars. Tighter limits were dropping ~20% of pairs.
    rationale: str = Field(max_length=2500)


class BaselineRecord(BaseModel):
    """Output of the single-pass GPT-4-equivalent baseline. Catalog + label + enriched
    delivered in one mega-prompt — the *single pass* is the experimental variable.
    See docs/07-evaluation.md §Pair construction."""

    catalog: CatalogFields
    label: LabelFields
    enriched: EnrichedPayload
    overall_confidence: float = Field(ge=0, le=1)


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


def _truncate(text: str, pass_name: str) -> str:
    """Clip text to ~4 chars per token under the pass's input_cap budget.

    Token≈4 chars is a rough heuristic; tiktoken would be more accurate but we
    avoid that coupling here. See docs/03 §Token budgets.
    """
    tokens = TOKEN_BUDGETS[pass_name]["input_cap"]
    return text[: 4 * tokens]


def _schema_for(model_class: type[BaseModel]) -> str:
    """Render a pydantic model's JSON schema as a pretty-printed string."""
    return json.dumps(model_class.model_json_schema(), indent=2)


def build_propose_user(document_text: str, references: list[dict], content_type_guess: str) -> str:
    """User message for the PROPOSE pass. See docs/03 §PROPOSE prompt."""
    doc = _truncate(document_text, "propose")
    n = TOKEN_BUDGETS["propose"]["input_cap"]
    return f"""\
Document type guess: {content_type_guess}
Document text (truncated to {n} tokens):
{doc}

References extracted:
{json.dumps(references, indent=2)}

Task: produce a ProposalRecord covering catalog (content type, ownership,
compliance, commercial viability) AND label (methodology, novelty,
evidence, claim graph, citations, domain tags). Cite source evidence
inline in rationales where possible.

Schema:
{_schema_for(ProposalRecord)}"""


def build_critique_user(proposal: ProposalRecord, document_text: str, idx: int, n: int) -> str:
    """User message for the CRITIQUE pass. See docs/03 §CRITIQUE prompt."""
    doc = _truncate(document_text, "critique")
    return f"""\
Proposal under review (index {idx} of {n}):
{proposal.model_dump_json(indent=2)}

Original document (truncated):
{doc}

Task: critique each field in the proposal. Flag fields that are
too vague, wrong, missing evidence, or contradicted by the source.
For each critiqued field, suggest a specific revision. Then give
an overall assessment.

Pay particular attention to compliance flags — check the heuristics
above against the document text. Missed compliance flags are the
most expensive type of error.

Schema:
{_schema_for(Critique)}"""


def build_refine_user(proposal: ProposalRecord, critique: Critique, document_text: str) -> str:
    """User message for the REFINE pass. See docs/03 §REFINE prompt."""
    doc = _truncate(document_text, "refine")
    return f"""\
Original proposal:
{proposal.model_dump_json(indent=2)}

Critique:
{critique.model_dump_json(indent=2)}

Original document (truncated):
{doc}

Task: produce a revised RefinedRecord. Apply every "wrong" or
"contradicted_by_source" critique. Apply "too_vague" critiques
unless source evidence is genuinely thin. Add a revision_summary
explaining what changed and why.

Schema:
{_schema_for(RefinedRecord)}"""


def build_vote_user(refined: list[RefinedRecord], document_text: str) -> str:
    """User message for the VOTE pass. See docs/03 §VOTE prompt."""
    doc = _truncate(document_text, "vote")
    n = len(refined)
    records_json = json.dumps([r.model_dump() for r in refined], indent=2)
    return f"""\
Refined records under consideration ({n} candidates):
{records_json}

Original document (truncated):
{doc}

Task: pick the strongest record. "Strongest" means:
  - Highest specificity on methodology
  - Strongest source-grounded novelty claim
  - Most defensible compliance flags (false negatives are worse than false positives)
  - Internally consistent across catalog and label

Output the winner_idx, your confidence, and a one-sentence rationale.

Schema:
{_schema_for(VoteResult)}"""


def build_enrich_user(winning_refined: RefinedRecord, document_text: str) -> str:
    """User message for the ENRICH pass. See docs/03 §ENRICH prompt."""
    doc = _truncate(document_text, "enrich")
    n = TOKEN_BUDGETS["enrich"]["input_cap"]
    return f"""\
Winning record:
{winning_refined.model_dump_json(indent=2)}

Original document (full text up to {n} tokens):
{doc}

Task: produce an EnrichedPayload — the AI-lab-ready metadata.
  - expanded_abstract: 500–800 words, structured narrative
  - novelty_rationale: why this contribution is novel; cite prior work
  - citation_context: for each citation, classify as motivation, comparison,
                      methodology, or background, with a supporting quote
  - claim_graph_v2: refined claim graph with claim_strength enum
  - derived_keywords: 5–15 tags useful for retrieval
  - suggested_buyer_segments: which kind of AI lab would value this

Schema:
{_schema_for(EnrichedPayload)}"""


# Token budgets per pass — drives truncation and the cost meter.
# See docs/03-prompts-and-schemas.md §Token budgets.
TOKEN_BUDGETS = {
    "propose": {"input_cap": 6000, "output_cap": 1500},
    "critique": {"input_cap": 4000, "output_cap": 800},
    "refine": {"input_cap": 5000, "output_cap": 1500},
    "vote": {"input_cap": 3000, "output_cap": 300},
    "enrich": {"input_cap": 8000, "output_cap": 2500},
    "judge": {"input_cap": 6000, "output_cap": 700},
    "baseline": {"input_cap": 8000, "output_cap": 3000},
}

# Temperature per pass — see docs/02-agent-loop.md §Determinism knobs.
PASS_TEMPERATURE = {
    "propose": 0.8,
    "critique": 0.4,
    "refine": 0.2,
    "vote": 0.0,
    "enrich": 0.5,
    "judge": 0.0,
    "baseline": 0.2,
}


def build_judge_user(
    record_a: dict,
    record_b: dict,
    document_text: str,
    rubric_yaml: str,
) -> str:
    """User message for the JUDGE pass. See docs/07-evaluation.md §Blinding.

    The judge receives the two records as A and B with the blinding map
    *not* disclosed. Rubric YAML is injected verbatim so dimension definitions
    are visible to the model.
    """
    doc = _truncate(document_text, "judge")
    n = TOKEN_BUDGETS["judge"]["input_cap"]
    return f"""\
You are evaluating two candidate label records (A and B) for the same source
document. The ordering between A and B is randomized — DO NOT try to guess
which side came from a multi-pass loop vs a single-pass call. Score on
label quality only.

Dimension rubrics (1–5 per dimension, per record):
{rubric_yaml}

Record A:
{json.dumps(record_a, indent=2)}

Record B:
{json.dumps(record_b, indent=2)}

Source document (truncated to {n} tokens):
{doc}

Task: produce a JudgeOutput. For each record, score every dimension on the
1–5 rubric above. Then pick a winner ("A", "B", or "tie") and give a
one-paragraph rationale grounded in specific differences between A and B.
A win means clearly better label quality, not just a stylistic preference.

Schema:
{_schema_for(JudgeOutput)}"""


def build_gpt4_baseline_user(
    document_text: str,
    references: list[dict],
    content_type_guess: str,
) -> str:
    """User message for the GPT-4-equivalent single-pass baseline.

    One mega-prompt: produce catalog + label + enriched payload in a single
    call. This is what a naive single-pass labeler would do without the
    propose → critique → refine → vote → enrich loop. See
    docs/07-evaluation.md §Pair construction.
    """
    doc = _truncate(document_text, "baseline")
    n = TOKEN_BUDGETS["baseline"]["input_cap"]
    return f"""\
Document type guess: {content_type_guess}
Document text (truncated to {n} tokens):
{doc}

References extracted:
{json.dumps(references, indent=2)}

Task: in a SINGLE response, produce a BaselineRecord that combines:
  - catalog: content_type, ownership, compliance_flags, commercial_score/action
  - label: structured_abstract, methodology, novelty_claim, evidence,
           claim_graph, citations, domain_tags
  - enriched: expanded_abstract, novelty_rationale, citation_context,
              claim_graph_v2, derived_keywords, suggested_buyer_segments

You have one shot — no critique step. Be specific where the source supports
it; mark fields unclear/low-confidence where it doesn't.

Schema:
{_schema_for(BaselineRecord)}"""
