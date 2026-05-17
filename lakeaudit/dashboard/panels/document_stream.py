"""Panel 1: Document stream — docs/sec counter + latest 20 finalized records.

Refresh: 1Hz. Query: lakeaudit.dashboard.queries.LATEST_RECORDS + DOCS_PER_SEC_COUNTER.
See docs/06-dashboard.md §Panel 1.
"""

from __future__ import annotations

import streamlit as st


def render(run_id: str) -> None:
    st.subheader("1. Document stream")
    raise NotImplementedError(
        "TODO: query LATEST_RECORDS + DOCS_PER_SEC_COUNTER, render counters + table. "
        "Compute docs/sec in Python from delta since previous poll (st.session_state)."
    )
