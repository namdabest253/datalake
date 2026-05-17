# 03. Prompts and schemas

Per-pass prompt templates and JSON schemas (as pydantic v2 models). Single source of truth for taxonomies. Compliance heuristics live in `lakeaudit/prompts/heuristics.yaml`.

## Prompt-design principles

- **One mega-prompt per pass, not per field.** Cheaper (less per-call overhead), more coherent (model holds full context), and faster (fewer round trips).
- **System message holds taxonomies + role.** User message holds the document chunk + task. Taxonomies change only at deploy time; doc text changes every call. This shape maximizes prompt-cache hit rate on Wafer.
- **Single source of truth for taxonomies.** All enum strings live in `lakeaudit/prompts/taxonomies.py`. Prompts string-format from there. Pydantic models import the same constants. No drift between schema and prompt.
- **Few-shot exemplars: max 1–2 per pass.** Token budget; the model is already strong.
- **Validate every output with pydantic.** Treat validation failure as a pass failure — one repair retry, then fail. See [`05`](05-inference-client.md) for retry mechanics.

## Structured-output strategy

Prefer Wafer's JSON-schema mode (`response_format={"type": "json_schema", "schema": ...}`) if supported — verify against Wafer docs on day 1.

If unsupported, fall back to:

1. Prompt instructions: `"Respond with valid JSON only. Schema: {...}"`
2. `json.loads` on the response body.
3. On parse or pydantic-validation failure, one repair retry: original messages + `assistant: {bad_output}` + `user: please return valid JSON matching the schema above; no prose.`
4. Second failure = pass failure.

## Taxonomies (single source of truth — `lakeaudit/prompts/taxonomies.py`)

```python
from enum import Enum

class ContentType(str, Enum):
    research_paper = "research_paper"
    grant_proposal = "grant_proposal"
    dataset_description = "dataset_description"
    faculty_publication = "faculty_publication"
    other = "other"

class Ownership(str, Enum):
    institution = "institution"
    faculty = "faculty"
    third_party_publisher = "third_party_publisher"
    funder = "funder"
    joint = "joint"
    unclear = "unclear"

class ComplianceFlag(str, Enum):
    ferpa = "ferpa"
    hipaa = "hipaa"
    irb_restricted = "irb_restricted"
    publisher_exclusive = "publisher_exclusive"
    public_domain = "public_domain"
    clean = "clean"
    unclear = "unclear"

class CommercialAction(str, Enum):
    license_ready = "license_ready"
    needs_consent = "needs_consent"
    do_not_sell = "do_not_sell"
    archive = "archive"

# ~30 named techniques; everything else goes into LabelFields.methodology_other_freetext
METHODOLOGY_NAMED = [
    "rct", "double_blind_rct", "cohort_study", "case_control",
    "cross_sectional_survey", "longitudinal_survey", "meta_analysis",
    "systematic_review", "ethnography", "case_study", "grounded_theory",
    "thematic_analysis", "regression_analysis", "structural_equation_model",
    "bayesian_inference", "monte_carlo_simulation", "agent_based_model",
    "finite_element_simulation", "ab_test", "wet_lab_experiment",
    "computational_modeling", "fine_tuned_llm", "fine_tuned_bert",
    "transformer_from_scratch", "contrastive_learning", "rl_from_human_feedback",
    "graph_neural_network", "knn_baseline", "literature_review",
    "theoretical_proof",
]
```

## JSON schemas (pydantic v2 — `lakeaudit/prompts/templates.py`)

### `ProposalRecord` (output of PROPOSE pass)

```python
from pydantic import BaseModel, Field
from typing import Literal

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
    structured_abstract: dict[Literal["problem","approach","findings","limitations"], str]
    methodology_named: list[str]          # subset of METHODOLOGY_NAMED
    methodology_other_freetext: str | None = None
    novelty_claim: str = Field(max_length=500)
    evidence_type: Literal["empirical","theoretical","simulation","survey","mixed"]
    evidence_strength: Literal["weak","moderate","strong"]
    sample_size: int | None = None
    claim_graph: list[dict]               # [{claim:str, evidence_pointer:str}]
    citations: list[dict]                 # [{title, authors, year, type}]
    domain_tags: list[str]                # field + subfield + application area

class ProposalRecord(BaseModel):
    catalog: CatalogFields
    label: LabelFields
    overall_confidence: float = Field(ge=0, le=1)
```

### `Critique` (output of CRITIQUE pass)

```python
class FieldCritique(BaseModel):
    field_path: str   # e.g. "label.methodology_named"
    issue: Literal["too_vague", "wrong", "missing_evidence", "contradicted_by_source", "ok"]
    suggestion: str | None = None

class Critique(BaseModel):
    proposal_idx: int
    field_critiques: list[FieldCritique]
    overall_assessment: Literal["accept", "revise", "reject"]
    rationale: str = Field(max_length=300)
```

### `RefinedRecord` (output of REFINE pass)

Same shape as `ProposalRecord` with an added `revision_summary` field:

```python
class RefinedRecord(ProposalRecord):
    revision_summary: str = Field(max_length=300)
```

### `VoteResult` (output of VOTE pass)

```python
class VoteResult(BaseModel):
    winner_idx: int
    winner_confidence: float = Field(ge=0, le=1)
    rationale: str = Field(max_length=300)
    runners_up: list[int] = Field(default_factory=list)
```

### `EnrichedPayload` (output of ENRICH pass)

```python
class EnrichedPayload(BaseModel):
    expanded_abstract: str = Field(max_length=2000)
    novelty_rationale: str = Field(max_length=800)
    citation_context: list[dict]   # [{cited_work_idx, function: "motivation|comparison|methodology|background", quote: str}]
    claim_graph_v2: list[dict]     # claim_graph with stronger evidence pointers + claim_strength enum
    derived_keywords: list[str]
    suggested_buyer_segments: list[Literal["frontier_lab","domain_specialist","data_marketplace","academic_archive"]]
```

### Judge schema (consumed by eval — `lakeaudit/eval/judge_runner.py`)

```python
class DimensionScore(BaseModel):
    methodology_specificity: int = Field(ge=1, le=5)
    novelty_claim_accuracy: int = Field(ge=1, le=5)
    evidence_quality: int = Field(ge=1, le=5)
    citation_completeness: int = Field(ge=1, le=5)
    compliance_correctness: int = Field(ge=1, le=5)
    ownership_defensibility: int = Field(ge=1, le=5)

class JudgeOutput(BaseModel):
    winner: Literal["A", "B", "tie"]
    a_scores: DimensionScore
    b_scores: DimensionScore
    rationale: str = Field(max_length=500)
```

## Compliance heuristics (`lakeaudit/prompts/heuristics.yaml`)

Loaded at start of `lakeaudit run`, injected into the CRITIQUE pass's system prompt. Editable on stage between runs (PRD §11).

```yaml
# Each rule: a signal in the document → a compliance flag the critic should ensure is set
ferpa:
  - "explicit student names + grades or transcripts"
  - "mention of FERPA / education records / Family Educational Rights"

hipaa:
  - "patient identifiers + clinical observations"
  - "mention of HIPAA / protected health information / PHI"

irb_restricted:
  - "human subjects research described"
  - "informed consent language"
  - "IRB approval number cited"

publisher_exclusive:
  - "publisher copyright notice with exclusive license language"
  - "journal-of-record metadata that implies transferred rights"
  - "ACM / IEEE / Elsevier copyright transfer mention"

public_domain:
  - "government work / federal employee authorship"
  - "explicit CC-BY-0 or PD dedication"

clean:
  - "preprint with CC-BY"
  - "university-press-released dataset with explicit license to redistribute"
```

**Hot-reload: between runs only, never mid-run.** Within-run changes would produce inconsistent records inside one corpus. The file is read once in `lakeaudit run`'s startup; subsequent edits require a re-run of the affected slice.

## Prompt templates (verbatim — `lakeaudit/prompts/templates.py`)

Shared system message shape (across passes):

```
You are a {role} for LakeAudit, a university data-preparation system.

Taxonomies you MUST use (do not invent values):
  content_type:       {ContentType values}
  ownership:          {Ownership values}
  compliance_flags:   {ComplianceFlag values}
  commercial_action:  {CommercialAction values}
  methodology_named:  {METHODOLOGY_NAMED}

Compliance heuristics:
{rendered heuristics.yaml}

Respond with valid JSON matching the provided schema. No prose.
```

### PROPOSE prompt (user msg)

```
Document type guess: {content_type_guess}
Document text (truncated to {N} tokens):
{document.text[:N]}

References extracted:
{document.references}

Task: produce a ProposalRecord covering catalog (content type, ownership,
compliance, commercial viability) AND label (methodology, novelty,
evidence, claim graph, citations, domain tags). Cite source evidence
inline in rationales where possible.

Schema: {ProposalRecord JSON schema}
```

### CRITIQUE prompt (user msg)

```
Proposal under review (index {i} of {N}):
{proposal as JSON}

Original document (truncated):
{document.text[:N]}

Task: critique each field in the proposal. Flag fields that are
too vague, wrong, missing evidence, or contradicted by the source.
For each critiqued field, suggest a specific revision. Then give
an overall assessment.

Pay particular attention to compliance flags — check the heuristics
above against the document text. Missed compliance flags are the
most expensive type of error.

Schema: {Critique JSON schema}
```

### REFINE prompt (user msg)

```
Original proposal:
{proposal as JSON}

Critique:
{critique as JSON}

Original document (truncated):
{document.text[:N]}

Task: produce a revised RefinedRecord. Apply every "wrong" or
"contradicted_by_source" critique. Apply "too_vague" critiques
unless source evidence is genuinely thin. Add a revision_summary
explaining what changed and why.

Schema: {RefinedRecord JSON schema}
```

### VOTE prompt (user msg)

```
Refined records under consideration ({N} candidates):
{[refined_record_1, refined_record_2, ...] as JSON}

Original document (truncated):
{document.text[:N]}

Task: pick the strongest record. "Strongest" means:
  - Highest specificity on methodology
  - Strongest source-grounded novelty claim
  - Most defensible compliance flags (false negatives are worse than false positives)
  - Internally consistent across catalog and label

Output the winner_idx, your confidence, and a one-sentence rationale.

Schema: {VoteResult JSON schema}
```

### ENRICH prompt (user msg)

```
Winning record:
{winning_refined_record as JSON}

Original document (full text up to {N} tokens):
{document.text[:N]}

Task: produce an EnrichedPayload — the AI-lab-ready metadata.
  - expanded_abstract: 500–800 words, structured narrative
  - novelty_rationale: why this contribution is novel; cite prior work
  - citation_context: for each citation, classify as motivation, comparison,
                      methodology, or background, with a supporting quote
  - claim_graph_v2: refined claim graph with claim_strength enum
  - derived_keywords: 5–15 tags useful for retrieval
  - suggested_buyer_segments: which kind of AI lab would value this

Schema: {EnrichedPayload JSON schema}
```

### JUDGE prompt (eval — user msg)

```
Two records produced for the same document, by different pipelines.
Labels A and B are randomized — you do not know which is which.

Record A:
{record_a as JSON}

Record B:
{record_b as JSON}

Original document (truncated):
{document.text[:N]}

Task: score each record 1–5 on each of:
  - methodology_specificity   (vague vs precise named techniques)
  - novelty_claim_accuracy    (matches source vs hallucinated)
  - evidence_quality          (well-supported vs hand-wave)
  - citation_completeness     (citations parsed and classified vs missing)
  - compliance_correctness    (flags supported by document text)
  - ownership_defensibility   (rationale grounded in document)

Then declare a winner: A, B, or tie. One-sentence rationale.

Schema: {JudgeOutput JSON schema}
```

## Token budgets

Per pass, expected tokens (input + output):

| Pass | Input cap | Output cap | Notes |
|---|---|---|---|
| PROPOSE | 6,000 | 1,500 | Largest input — doc text dominates |
| CRITIQUE | 4,000 | 800 | Doc text truncated more aggressively (critic doesn't need full doc) |
| REFINE | 5,000 | 1,500 | Proposal + critique + doc snippet |
| VOTE | 3,000 | 300 | Compact — refined records only, doc snippet for tie-break |
| ENRICH | 8,000 | 2,500 | Wants full doc context, larger output |
| JUDGE | 6,000 | 700 | Both records + doc snippet |

These cap the cost meter and drive the GPT-4 foil calculation in [`05`](05-inference-client.md).
