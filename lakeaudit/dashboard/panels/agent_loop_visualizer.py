"""Panel 2: Agent loop visualizer — render the propose → critique → refine → vote → enrich tree.

Refresh: 250ms (faster than the rest). Picks a verbose-traced doc (every Kth, K=10)
and animates its trace_events tree. Hover shows prompt/response.
See docs/06-dashboard.md §Panel 2 and docs/02-agent-loop.md §Trace contract.
"""

from __future__ import annotations

import streamlit as st


def render(run_id: str) -> None:
    st.subheader("2. Agent loop visualizer")
    raise NotImplementedError(
        "TODO: PICK_VERBOSE_TRACED_DOC, then TRACE_FOR_DOC. "
        "Render as a tree (Graphviz via st.graphviz_chart or streamlit-elements). "
        "Use a 250ms refresh inside this panel via a separate st_autorefresh key."
    )
