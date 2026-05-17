"""JSONL writer matching the export schema in docs/04-data-model.md.

Custom MVP schema — not pinned to Anthropic or OpenAI fine-tune format.
Resolves PRD §15 #4.
"""

from __future__ import annotations

import json
from pathlib import Path


async def export_jsonl(run_id: str, db_path: Path, out_path: Path) -> int:
    """Write one JSON object per line. Returns row count.

    Schema: {id, source_path, source_hash, run_id, catalog{...}, label{...},
             trace_summary{...}, costs{wafer_usd, gpt4_equivalent_usd,
             human_labeler_equivalent_usd}, model_versions{...}}
    """
    raise NotImplementedError(
        "TODO: JOIN documents + catalog_records + label_payloads + costs, "
        "render the JSONL row per docs/04 §JSONL export schema."
    )


def render_row(
    document: dict,
    catalog: dict,
    label: dict,
    trace_summary: dict,
    costs: dict,
    model_versions: dict,
) -> str:
    """Serialize one row as JSONL. Inputs match the SQL JOIN result shape."""
    return json.dumps(
        {
            "id": document["id"],
            "source_path": document["source_path"],
            "source_hash": document["source_hash"],
            "run_id": document["run_id"],
            "catalog": catalog,
            "label": label,
            "trace_summary": trace_summary,
            "costs": costs,
            "model_versions": model_versions,
        },
        ensure_ascii=False,
    )
