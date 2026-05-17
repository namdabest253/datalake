"""Panel 5: Catalog filter view — post-run, filter by compliance + commercial score.

Estimated total market value = sum over license-ready docs of per-content-type dollar table.
See docs/06-dashboard.md §Panel 5.
"""

from __future__ import annotations

import json

import streamlit as st

from datalake.dashboard._db import read
from datalake.prompts.taxonomies import CommercialAction, ComplianceFlag

# Per-doc estimated lifetime commercial value to AI labs as labeled training data.
# Basis: PRD §3 establishes ~$1–$10 per high-quality scientific datapoint as the
# buyer-side price. A research paper typically yields tens to low hundreds of
# datapoints (sections, claims, QA pairs), putting per-paper values in the
# $100–$1,500 range. Numbers below are demo-grade midpoints; tune against real
# buyer conversations before claiming a hard market value to the institution.
ESTIMATED_VALUE_PER_DOC: dict[str, int] = {
    "research_paper": 800,
    "grant_proposal": 200,
    "dataset_description": 1500,
    "faculty_publication": 600,
    "other": 100,
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
    from datalake.dashboard._db import db_path
    import sqlite3

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

    total_value = sum(ESTIMATED_VALUE_PER_DOC.get(r["content_type"], 100) for r in rows)
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
