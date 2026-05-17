"""Win rate, quality delta math, cost ratio. See docs/07-evaluation.md §Scoring math."""

from __future__ import annotations

from statistics import mean

DIMENSIONS = [
    "methodology_specificity",
    "novelty_claim_accuracy",
    "evidence_quality",
    "citation_completeness",
    "compliance_correctness",
    "ownership_defensibility",
]

# Equal weights by default. Tunable — upweight compliance_correctness if false negatives bite.
DIMENSION_WEIGHTS: dict[str, float] = {d: 1.0 for d in DIMENSIONS}


def resolve_winner(a_is_datalake: bool, judge_winner: str) -> str:
    """Unblind: convert judge's A/B/tie into datalake/gpt4/tie."""
    if judge_winner == "tie":
        return "tie"
    if judge_winner == "A":
        return "datalake" if a_is_datalake else "gpt4"
    return "gpt4" if a_is_datalake else "datalake"


def compute_win_rate(unblinded_winners: list[str]) -> float:
    """Win rate excludes ties from the denominator."""
    decisive = [w for w in unblinded_winners if w != "tie"]
    if not decisive:
        return 0.0
    return sum(1 for w in decisive if w == "datalake") / len(decisive)


def compute_dimension_deltas(pair_scores: list[dict]) -> dict[str, float]:
    """Per-dimension mean(datalake_score − gpt4_score) across pairs.

    pair_scores rows: {"datalake": {dim: int}, "gpt4": {dim: int}} per pair.
    """
    return {
        dim: mean(p["datalake"][dim] - p["gpt4"][dim] for p in pair_scores)
        for dim in DIMENSIONS
    }


def compute_cost_ratio(wafer_total_micro_usd: int, gpt4_total_micro_usd: int) -> float:
    """Returns wafer / gpt4 — target ≤ 0.3 per PRD §9."""
    if gpt4_total_micro_usd == 0:
        return 0.0
    return wafer_total_micro_usd / gpt4_total_micro_usd
