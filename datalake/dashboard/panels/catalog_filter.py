"""Panel 5: Catalog filter view — post-run, filter by compliance + commercial score.

Estimated total market value = sum over license-ready docs of per-content-type dollar table.
See docs/06-dashboard.md §Panel 5.
"""

from __future__ import annotations

import json

import streamlit as st

from datalake.prompts.taxonomies import CommercialAction, ComplianceFlag

# Per-doc estimated AI-training license value paid by labs to the institution.
# Anchors (2024–2025 disclosed/derived deals):
#   - HarperCollins ↔ Microsoft (Nov 2024): $5,000/book, 3yr — only fully
#     disclosed per-unit price in the market.
#   - Wiley AI deals FY24: $44M total across ~2M-article portfolio →
#     ~$10–$25/article (analyst-derived).
#   - Taylor & Francis ↔ Microsoft (May 2024): $10M upfront across ~3M
#     articles → ~$3–$5/article (analyst-derived).
#   - Surge/Scale PhD-tier annotation: $50–$100/example, $150–$350/hr (floor
#     for expert-labeled rates; used as analog for unpublished grant work).
# Treat these as midpoints with ±2× uncertainty — academic per-article deal
# counts are not disclosed. Earlier table ($100–$1,500/doc) conflated
# annotation cost with licensing revenue; these numbers reflect what AI labs
# actually pay rights-holders, not what vendors charge to label.
ESTIMATED_VALUE_PER_DOC: dict[str, int] = {
    "research_paper": 15,
    "grant_proposal": 50,
    "dataset_description": 5,
    "faculty_publication": 10,
    "other": 2,
}


def render(run_id: str) -> None:
    st.subheader("5. Catalog filter view (post-run)")

    col_a, col_b = st.columns([2, 1])
    with col_a:
        selected_actions = st.multiselect(
            "Commercial action",
            options=[a.value for a in CommercialAction],
            default=[CommercialAction.license_ready.value],
        )
    with col_b:
        min_score = st.slider("min commercial score", 0, 100, 50)

    if not selected_actions:
        st.caption("Select at least one commercial action.")
        return

    # The :selected_actions IN clause expansion can't use named params, so we
    # safely inline the enum-validated values.
    placeholders = ",".join(["?"] * len(selected_actions))
    sql = f"""
        SELECT d.id, d.source_path, c.content_type, c.commercial_action,
               c.commercial_score, c.compliance_flags
        FROM documents d
        JOIN catalog_records c ON c.doc_id = d.id
        WHERE d.run_id = ?
          AND c.commercial_action IN ({placeholders})
          AND c.commercial_score >= ?
        ORDER BY c.commercial_score DESC
    """
    import sqlite3

    from datalake.dashboard._db import db_path

    path = db_path()
    if not path.exists():
        st.caption("No catalog records yet.")
        return
    try:
        conn = sqlite3.connect(str(path))
        conn.row_factory = sqlite3.Row
        try:
            rows = conn.execute(
                sql, [run_id, *selected_actions, min_score]
            ).fetchall()
        finally:
            conn.close()
    except sqlite3.OperationalError:
        rows = []

    if not rows:
        st.caption("No docs match these filters yet.")
        return

    total_value = sum(
        ESTIMATED_VALUE_PER_DOC.get(r["content_type"], ESTIMATED_VALUE_PER_DOC["other"])
        for r in rows
    )
    c1, c2 = st.columns(2)
    c1.metric("matching docs", f"{len(rows):,}")
    c2.metric("est. market value", f"${total_value:,}")

    table = []
    for r in rows[:200]:
        try:
            flags = json.loads(r["compliance_flags"])
        except (TypeError, json.JSONDecodeError):
            flags = []
        table.append(
            {
                "source": r["source_path"].split("/")[-1],
                "type": r["content_type"],
                "action": r["commercial_action"],
                "score": r["commercial_score"],
                "compliance": ", ".join(flags) if flags else "—",
            }
        )
    st.dataframe(table, hide_index=True, use_container_width=True)
    if len(rows) > 200:
        st.caption(f"Showing first 200 of {len(rows):,} matches.")

    # Suppress unused-import warning for ComplianceFlag (kept for future filter expansion).
    _ = ComplianceFlag
