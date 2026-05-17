"""Calls the judge model on each (record_a, record_b) pair with blinded A/B.

Self-test required before each run: judge the canonical pair from
tests/fixtures/eval/canonical_pair.json and assert "LakeAudit wins, methodology delta ≥ +2".
See docs/07-evaluation.md §Self-test.
"""

from __future__ import annotations

import json
from pathlib import Path

from lakeaudit.inference.judge import JudgeClient
from lakeaudit.prompts.templates import JudgeOutput

CANONICAL_PAIR_PATH = Path("tests/fixtures/eval/canonical_pair.json")


async def run_judge(run_id: str, judge: JudgeClient) -> None:
    """Score every pair in eval_pairs, insert into eval_results.

    Blinding map (eval_pairs.a_is_lakeaudit) is NOT shown to the judge.
    """
    raise NotImplementedError("TODO: iterate eval_pairs, call judge, insert eval_results.")


async def judge_pair(record_a: dict, record_b: dict, document_text: str, judge: JudgeClient) -> JudgeOutput:
    """Single judge call. Returns the validated JudgeOutput schema."""
    raise NotImplementedError("TODO: render JUDGE prompt, call judge, validate as JudgeOutput.")


async def self_test(judge: JudgeClient) -> None:
    """Abort if the judge doesn't call the canonical pair the way it's supposed to.

    Catches: judge model regression, prompt template corruption, blinding-map bugs.
    """
    if not CANONICAL_PAIR_PATH.exists():
        raise FileNotFoundError(
            f"Canonical pair missing at {CANONICAL_PAIR_PATH}. "
            "See docs/07-evaluation.md §Self-test for the expected fixture format."
        )
    pair = json.loads(CANONICAL_PAIR_PATH.read_text())
    # Expected: judge picks the "good" side; methodology dimension delta ≥ +2.
    raise NotImplementedError("TODO: call judge_pair, assert expected outcome.")
