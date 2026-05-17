"""Single source of truth for taxonomy strings.

Pydantic models and prompt templates both import from here so they never drift.
See docs/03-prompts-and-schemas.md §Taxonomies.
"""

from __future__ import annotations

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


# ~30 named techniques. Anything outside this list goes into
# LabelFields.methodology_other_freetext. Keep this list short — adding entries
# requires re-running the corpus.
METHODOLOGY_NAMED: list[str] = [
    "rct",
    "double_blind_rct",
    "cohort_study",
    "case_control",
    "cross_sectional_survey",
    "longitudinal_survey",
    "meta_analysis",
    "systematic_review",
    "ethnography",
    "case_study",
    "grounded_theory",
    "thematic_analysis",
    "regression_analysis",
    "structural_equation_model",
    "bayesian_inference",
    "monte_carlo_simulation",
    "agent_based_model",
    "finite_element_simulation",
    "ab_test",
    "wet_lab_experiment",
    "computational_modeling",
    "fine_tuned_llm",
    "fine_tuned_bert",
    "transformer_from_scratch",
    "contrastive_learning",
    "rl_from_human_feedback",
    "graph_neural_network",
    "knn_baseline",
    "literature_review",
    "theoretical_proof",
]
