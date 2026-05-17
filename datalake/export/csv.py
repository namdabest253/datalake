"""Catalog CSV for the compliance team — flat columns, pipe-delimited compliance_flags.

See docs/04-data-model.md §Catalog CSV.
"""

from __future__ import annotations

from pathlib import Path

CATALOG_COLUMNS = [
    "doc_id",
    "source_path",
    "content_type",
    "content_type_confidence",
    "ownership",
    "ownership_confidence",
    "ownership_rationale",
    "compliance_flags",  # pipe-delimited
    "commercial_score",
    "commercial_action",
]


async def export_catalog_csv(run_id: str, db_path: Path, out_path: Path) -> int:
    """Write the catalog CSV. Returns row count."""
    raise NotImplementedError(
        "TODO: JOIN documents + catalog_records WHERE run_id=?, write CSV. "
        "compliance_flags column is the JSON array pipe-joined for spreadsheet readability."
    )


def render_row(catalog: dict, source_path: str) -> dict:
    """One CSV row dict. JSON array → pipe-delimited string."""
    flags = catalog["compliance_flags"]
    return {
        "doc_id": catalog["doc_id"],
        "source_path": source_path,
        "content_type": catalog["content_type"],
        "content_type_confidence": catalog["content_type_confidence"],
        "ownership": catalog["ownership"],
        "ownership_confidence": catalog["ownership_confidence"],
        "ownership_rationale": catalog["ownership_rationale"],
        "compliance_flags": "|".join(flags) if isinstance(flags, list) else flags,
        "commercial_score": catalog["commercial_score"],
        "commercial_action": catalog["commercial_action"],
    }
