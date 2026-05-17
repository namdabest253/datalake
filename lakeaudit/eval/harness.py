"""Eval orchestrator: run ~200 held-out docs through LakeAudit + single-pass GPT-4.

THE ONLY PLACE GPT-4 ACTUALLY EXECUTES end-to-end. Cost ~$1–5/doc baseline.
See docs/07-evaluation.md §Pair construction.
"""

from __future__ import annotations

from lakeaudit.config import Settings
from lakeaudit.inference.openai import OpenAIClient
from lakeaudit.inference.wafer import WaferClient


async def run_eval(
    n: int,
    run_id: str,
    settings: Settings,
    wafer: WaferClient,
    openai: OpenAIClient,
) -> None:
    """Sample n docs, run both pipelines, populate eval_pairs, then run the judge.

    1. Sample docs from documents table (diverse across content_type + discipline).
    2. For each: run LakeAudit loop AND single-pass GPT-4 with the combined catalog+label prompt.
    3. Insert eval_pairs(doc_id, lakeaudit_record, gpt4_record, a_is_lakeaudit=random()).
    4. Call lakeaudit.eval.judge_runner.run_judge to populate eval_results.
    """
    raise NotImplementedError("TODO: implement eval orchestration per docs/07")


async def gpt4_single_pass(doc, openai: OpenAIClient) -> dict:
    """Run the combined catalog + label payload as ONE GPT-4 call (the baseline)."""
    raise NotImplementedError(
        "TODO: build the combined mega-prompt and ask GPT-4 for the full record in one call."
    )
