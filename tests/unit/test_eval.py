"""Unit tests for the eval scoring + self-test path.

Covers:
- Scoring math: win-rate, dimension deltas, cost ratio, blind unmask.
- JudgeOutput / BaselineRecord pydantic round-trips.
- self_test passes when judge returns the expected outcome on the canonical pair.
- self_test raises when the judge gets it wrong (blinding-map bug, regression, etc.).

See docs/07-evaluation.md.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from pydantic import ValidationError

from datalake.eval import scoring
from datalake.eval.judge_runner import self_test
from datalake.inference.base import CallResult
from datalake.prompts.templates import (
    BaselineRecord,
    DimensionScore,
    JudgeOutput,
    build_gpt4_baseline_user,
    build_judge_user,
)

CANONICAL_PAIR_PATH = Path("tests/fixtures/eval/canonical_pair.json")


# ---------------------------------------------------------------------------
# Scoring math
# ---------------------------------------------------------------------------


def test_resolve_winner_unblinds_A_correctly() -> None:
    assert scoring.resolve_winner(a_is_datalake=True, judge_winner="A") == "datalake"
    assert scoring.resolve_winner(a_is_datalake=False, judge_winner="A") == "gpt4"


def test_resolve_winner_unblinds_B_correctly() -> None:
    assert scoring.resolve_winner(a_is_datalake=True, judge_winner="B") == "gpt4"
    assert scoring.resolve_winner(a_is_datalake=False, judge_winner="B") == "datalake"


def test_resolve_winner_passes_tie_through() -> None:
    assert scoring.resolve_winner(a_is_datalake=True, judge_winner="tie") == "tie"


def test_compute_win_rate_excludes_ties_from_denominator() -> None:
    winners = ["datalake", "datalake", "datalake", "gpt4", "tie", "tie"]
    # 3 datalake / 4 decided
    assert scoring.compute_win_rate(winners) == pytest.approx(0.75)


def test_compute_win_rate_returns_zero_when_no_decisive_pairs() -> None:
    assert scoring.compute_win_rate(["tie", "tie"]) == 0.0
    assert scoring.compute_win_rate([]) == 0.0


def test_compute_dimension_deltas_averages_across_pairs() -> None:
    pair_scores = [
        {
            "datalake": {d: 5 for d in scoring.DIMENSIONS},
            "gpt4": {d: 3 for d in scoring.DIMENSIONS},
        },
        {
            "datalake": {d: 4 for d in scoring.DIMENSIONS},
            "gpt4": {d: 2 for d in scoring.DIMENSIONS},
        },
    ]
    deltas = scoring.compute_dimension_deltas(pair_scores)
    for d in scoring.DIMENSIONS:
        assert deltas[d] == pytest.approx(2.0)


def test_compute_cost_ratio_target() -> None:
    # Wafer ~30x cheaper than GPT-4 ⇒ ratio ~0.033, well below 0.3.
    assert scoring.compute_cost_ratio(1_000, 30_000) == pytest.approx(1 / 30)
    assert scoring.compute_cost_ratio(100, 0) == 0.0  # guard


# ---------------------------------------------------------------------------
# Schema round-trips
# ---------------------------------------------------------------------------


def _dim_score_payload(value: int) -> dict:
    return {d: value for d in [
        "methodology_specificity",
        "novelty_claim_accuracy",
        "evidence_quality",
        "citation_completeness",
        "compliance_correctness",
        "ownership_defensibility",
    ]}


def test_judge_output_schema_roundtrip() -> None:
    payload = {
        "winner": "A",
        "a_scores": _dim_score_payload(5),
        "b_scores": _dim_score_payload(2),
        "rationale": "A has named methodologies, B has filler.",
    }
    out = JudgeOutput.model_validate(payload)
    assert out.winner == "A"
    assert out.a_scores.methodology_specificity == 5
    assert out.b_scores.methodology_specificity == 2


def test_judge_output_rejects_out_of_range_scores() -> None:
    payload = {
        "winner": "A",
        "a_scores": _dim_score_payload(6),  # > 5
        "b_scores": _dim_score_payload(3),
        "rationale": "x",
    }
    with pytest.raises(ValidationError):
        JudgeOutput.model_validate(payload)


def test_baseline_record_validates_from_canonical_fixture_datalake_side() -> None:
    pair = json.loads(CANONICAL_PAIR_PATH.read_text())
    # The canonical record doesn't carry an "enriched" key (it was hand-crafted
    # before BaselineRecord existed). Provide a minimal enriched payload to
    # satisfy schema; the loop output WILL include it in real runs.
    minimal_enriched = {
        "expanded_abstract": "x",
        "novelty_rationale": "y",
        "citation_context": [],
        "claim_graph_v2": [],
        "derived_keywords": [],
        "suggested_buyer_segments": ["frontier_lab"],
    }
    record = {**pair["datalake_record"], "enriched": minimal_enriched}
    BaselineRecord.model_validate(record)


# ---------------------------------------------------------------------------
# Prompt builders
# ---------------------------------------------------------------------------


def test_build_judge_user_includes_both_records_and_rubric() -> None:
    user = build_judge_user(
        record_a={"hello": "from_a"},
        record_b={"hello": "from_b"},
        document_text="ignored body",
        rubric_yaml="methodology_specificity:\n  5: 'specific'\n",
    )
    assert "from_a" in user
    assert "from_b" in user
    assert "methodology_specificity" in user
    # Blinding hint is in the prompt.
    assert "randomized" in user.lower()


def test_build_gpt4_baseline_user_demands_combined_record() -> None:
    user = build_gpt4_baseline_user(
        document_text="abc",
        references=[{"title": "ref"}],
        content_type_guess="research_paper",
    )
    assert "BaselineRecord" in user
    assert "single response" in user.lower() or "single" in user.lower()
    assert "research_paper" in user


# ---------------------------------------------------------------------------
# self_test — judge contract on the canonical fixture
# ---------------------------------------------------------------------------


class _StubJudgeClient:
    """Returns whatever JSON the test set up. Skips the network."""

    def __init__(self, payload: dict) -> None:
        self.payload = payload
        self.model = "stub-judge"

    async def call(
        self,
        system: str,
        user: str,
        *,
        json_schema: dict | None = None,
        temperature: float = 0.0,
        timeout: float = 20.0,
    ) -> CallResult:
        return CallResult(
            response_text=json.dumps(self.payload),
            tokens_in=10,
            tokens_out=10,
            cost_micro_usd=1,
            cost_basis="actual",
            latency_ms=1,
            model=self.model,
            provider="judge",
        )


@pytest.mark.asyncio
async def test_self_test_passes_when_judge_picks_A_with_methodology_delta_at_least_2() -> None:
    stub = _StubJudgeClient({
        "winner": "A",
        "a_scores": _dim_score_payload(5),
        "b_scores": _dim_score_payload(2),  # methodology delta = 3
        "rationale": "A names specific techniques.",
    })
    # Should not raise.
    await self_test(stub)


@pytest.mark.asyncio
async def test_self_test_raises_when_judge_picks_wrong_winner() -> None:
    stub = _StubJudgeClient({
        "winner": "B",
        "a_scores": _dim_score_payload(5),
        "b_scores": _dim_score_payload(2),
        "rationale": "I think B is better (this should not happen).",
    })
    with pytest.raises(RuntimeError, match="FAILED"):
        await self_test(stub)


@pytest.mark.asyncio
async def test_self_test_raises_when_methodology_delta_is_too_small() -> None:
    stub = _StubJudgeClient({
        "winner": "A",
        "a_scores": _dim_score_payload(3),
        "b_scores": _dim_score_payload(3),  # methodology delta = 0
        "rationale": "Tied on methodology — but A still wins overall.",
    })
    with pytest.raises(RuntimeError, match="FAILED"):
        await self_test(stub)


def test_dimension_score_round_trip() -> None:
    score = DimensionScore.model_validate(_dim_score_payload(4))
    assert score.compliance_correctness == 4
