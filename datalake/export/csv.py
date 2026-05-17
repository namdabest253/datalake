"""Catalog CSV for the compliance team — flat columns, pipe-delimited compliance_flags.

See docs/04-data-model.md §Catalog CSV.
"""

from __future__ import annotations

import csv
import json
from pathlib import Path

from datalake.storage.db import connect

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
    """Write the catalog CSV for all catalogued docs in this run. Returns row count."""
    out_path.parent.mkdir(parents=True, exist_ok=True)
    count = 0
    async with connect(db_path) as conn:
        cur = await conn.execute(
            "SELECT d.source_path, c.doc_id, c.content_type, c.content_type_confidence, "
            "       c.ownership, c.ownership_confidence, c.ownership_rationale, "
            "       c.compliance_flags, c.commercial_score, c.commercial_action "
            "FROM catalog_records c "
            "JOIN documents d ON d.id = c.doc_id "
            "WHERE d.run_id=? ORDER BY d.ingested_at",
            (run_id,),
        )
        rows = await cur.fetchall()
        with out_path.open("w", encoding="utf-8", newline="") as fh:
            writer = csv.DictWriter(fh, fieldnames=CATALOG_COLUMNS)
            writer.writeheader()
            for r in rows:
                catalog = {
                    "doc_id": r["doc_id"],
                    "content_type": r["content_type"],
                    "content_type_confidence": r["content_type_confidence"],
                    "ownership": r["ownership"],
                    "ownership_confidence": r["ownership_confidence"],
                    "ownership_rationale": r["ownership_rationale"],
                    "compliance_flags": _parse_flags(r["compliance_flags"]),
                    "commercial_score": r["commercial_score"],
                    "commercial_action": r["commercial_action"],
                }
                writer.writerow(render_row(catalog, r["source_path"]))
                count += 1
    return count


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


def _parse_flags(raw: str | None) -> list[str]:
    if raw is None:
        return []
    try:
        val = json.loads(raw)
        return val if isinstance(val, list) else []
    except (json.JSONDecodeError, TypeError):
        return []
