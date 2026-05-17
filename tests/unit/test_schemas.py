"""Pydantic schemas validate against canned API responses.

See docs/08-ops-and-demo.md §Testing strategy.
"""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from datalake.prompts.taxonomies import (
    CommercialAction,
    ComplianceFlag,
    ContentType,
    Ownership,
)
from datalake.prompts.templates import (
    CatalogFields,
    Critique,
    LabelFields,
    ProposalRecord,
    VoteResult,
)


def _valid_catalog_payload() -> dict:
    return {
        "content_type": ContentType.research_paper,
        "content_type_confidence": 0.9,
        "ownership": Ownership.institution,
        "ownership_confidence": 0.8,
        "ownership_rationale": "Authors list university affiliation; NSF grant cited.",
        "compliance_flags": [ComplianceFlag.clean],
        "commercial_score": 87,
        "commercial_action": CommercialAction.license_ready,
    }


def _valid_label_payload() -> dict:
    return {
        "structured_abstract": {
            "problem": "X",
            "approach": "Y",
            "findings": "Z",
            "limitations": "W",
        },
        "methodology_named": ["fine_tuned_bert"],
        "methodology_other_freetext": None,
        "novelty_claim": "First application of contrastive learning to ...",
        "evidence_type": "empirical",
        "evidence_strength": "strong",
        "sample_size": 12000,
        "claim_graph": [{"claim": "...", "evidence_pointer": "Section 4.2"}],
        "citations": [{"title": "...", "authors": ["..."], "year": 2022, "type": "comparison"}],
        "domain_tags": ["ml", "nlp"],
    }


def test_catalog_fields_round_trip() -> None:
    payload = _valid_catalog_payload()
    catalog = CatalogFields.model_validate(payload)
    assert catalog.commercial_score == 87
    assert catalog.commercial_action == CommercialAction.license_ready


def test_label_fields_round_trip() -> None:
    payload = _valid_label_payload()
    label = LabelFields.model_validate(payload)
    assert "fine_tuned_bert" in label.methodology_named


def test_proposal_record_round_trip() -> None:
    proposal = ProposalRecord.model_validate(
        {
            "catalog": _valid_catalog_payload(),
            "label": _valid_label_payload(),
            "overall_confidence": 0.84,
        }
    )
    assert 0 <= proposal.overall_confidence <= 1


def test_invalid_confidence_rejected() -> None:
    bad = _valid_catalog_payload() | {"content_type_confidence": 1.5}
    with pytest.raises(ValidationError):
        CatalogFields.model_validate(bad)


def test_critique_schema() -> None:
    crit = Critique.model_validate(
        {
            "proposal_idx": 0,
            "field_critiques": [
                {
                    "field_path": "label.methodology_named",
                    "issue": "too_vague",
                    "suggestion": "Name the specific BERT variant.",
                }
            ],
            "overall_assessment": "revise",
            "rationale": "Methodology needs specificity.",
        }
    )
    assert crit.overall_assessment == "revise"


def test_vote_result_schema() -> None:
    vote = VoteResult.model_validate(
        {"winner_idx": 1, "winner_confidence": 0.92, "rationale": "Best methodology specificity.", "runners_up": [0, 2]}
    )
    assert vote.winner_idx == 1
