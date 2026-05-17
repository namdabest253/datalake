"""Panel 5: Catalog filter view — post-run, filter by compliance + commercial score.

Estimated total market value = sum over license-ready docs of per-content-type dollar table.
See docs/06-dashboard.md §Panel 5.
"""

from __future__ import annotations

import streamlit as st

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
    raise NotImplementedError(
        "TODO: multiselect on compliance flags + commercial action; slider for min_score. "
        "Query FILTERED_CATALOG. Render table + estimated market value chip "
        "(sum over license-ready of ESTIMATED_VALUE_PER_DOC[content_type])."
    )
