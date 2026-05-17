"""Cost accounting math: GPT-4 estimation, human-labeler foil, kill switch.

See docs/05-inference-client.md §Competitive foils, §Hard kill switch.
"""

from __future__ import annotations

from datalake.inference.accounting import (
    GPT4_PRICING,
    HUMAN_LABELER_PRICING_PER_DOC_USD,
    estimate_gpt4_cost,
)


def test_estimate_gpt4_cost_input_only() -> None:
    """1M input tokens at $10/M = $10 = 10_000_000 micro-USD."""
    assert estimate_gpt4_cost(tokens_in=1_000_000, tokens_out=0) == 10_000_000


def test_estimate_gpt4_cost_output_only() -> None:
    """1M output tokens at $30/M = $30 = 30_000_000 micro-USD."""
    assert estimate_gpt4_cost(tokens_in=0, tokens_out=1_000_000) == 30_000_000


def test_estimate_gpt4_cost_mixed() -> None:
    """5k in, 1.5k out at gpt-4-turbo prices."""
    expected = int((5000 * 10.0 + 1500 * 30.0) / 1_000_000 * 1_000_000)
    assert estimate_gpt4_cost(tokens_in=5000, tokens_out=1500) == expected


def test_human_labeler_pricing_has_all_content_types() -> None:
    """Every ContentType enum value must have a default per-doc price (no KeyError at runtime)."""
    from datalake.prompts.taxonomies import ContentType

    for ct in ContentType:
        assert ct.value in HUMAN_LABELER_PRICING_PER_DOC_USD


def test_pricing_constants_documented_source() -> None:
    """Sanity check pricing constants are within the orders of magnitude PRD §3 quotes."""
    assert GPT4_PRICING["gpt-4-turbo"]["input_per_million"] > 0
    # Per PRD §3, Surge-tier scientific labeling is $30–$60/paper. Default midpoint is in band.
    assert 20 <= HUMAN_LABELER_PRICING_PER_DOC_USD["research_paper"] <= 100
