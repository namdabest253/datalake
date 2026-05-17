"""Panel 3: Quality metrics — avg confidence, low-conf flag rate, inter-agent agreement.

Refresh: 1Hz. See docs/06-dashboard.md §Panel 3.
"""

from __future__ import annotations

import streamlit as st


def render(run_id: str) -> None:
    st.subheader("3. Quality metrics")
    raise NotImplementedError(
        "TODO: query QUALITY_COUNTERS + LOW_CONF_FLAG_RATE. "
        "Inter-agent agreement = fraction of docs where ≥2 of 3 proposers agreed on "
        "content_type AND ownership — derive from trace_events.proposal_idx grouping."
    )
