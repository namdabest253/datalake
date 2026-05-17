"""Auto-generated dataset_card.md from SQL aggregates over a completed run.

See docs/04-data-model.md §dataset_card.md auto-generation.
"""

from __future__ import annotations

from pathlib import Path

DATASET_CARD_TEMPLATE = """\
# LakeAudit dataset card

- **Run ID**: {run_id}
- **Corpus version**: {corpus_version}
- **Docs total**: {docs_total}
- **Docs done**: {docs_done} ({pct_done:.1f}%)
- **Docs partial (catalog only)**: {docs_partial}
- **Docs failed**: {docs_failed}

## Catalog distribution
- Content types: {content_type_counts}
- Ownership: {ownership_counts}
- Commercial actions: {commercial_action_counts}
- License-ready docs: {license_ready_count} ({license_ready_pct:.1f}%)

## Label quality (vs single-pass GPT-4 on 200-doc eval subset)
- LakeAudit win rate: {win_rate_pct:.1f}%
- Quality delta by dimension: {dimension_deltas}
- LakeAudit cost per doc: ${wafer_cost_per_doc:.4f}
- GPT-4 cost per doc: ${gpt4_cost_per_doc:.4f}
- LakeAudit / GPT-4 cost ratio: {cost_ratio:.3f}

## Models used
{model_versions_table}

## Methodology
LakeAudit ran a 6-pass agent loop (propose × 3 → critique × 3 → refine × 3 → vote → enrich)
on Wafer Serverless. GPT-4 baseline ran single-pass with the same combined prompt.
Judge: {judge_model}, blinded A/B comparison.

GPT-4 foil cost in the dashboard cost meter is **estimated** (tokens × public pricing);
GPT-4 was only actually run on the 200-doc eval subset. The human-labeler foil
($30–$60/paper Surge-tier rate per PRD §3) is reference-only — no human labels are produced.
"""


async def render_dataset_card(run_id: str, db_path: Path, out_path: Path) -> None:
    """Populate the template from SQL aggregates and write to out_path."""
    raise NotImplementedError(
        "TODO: collect aggregates (corpus_version, doc counts, content_type histogram, "
        "ownership histogram, license-ready count, eval metrics, model_versions), "
        "format DATASET_CARD_TEMPLATE, write."
    )
