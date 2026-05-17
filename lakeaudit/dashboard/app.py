"""Streamlit entrypoint. Single page, six panels.

Run: `streamlit run lakeaudit/dashboard/app.py` (or `lakeaudit dashboard`).
See docs/06-dashboard.md §Page layout.
"""

from __future__ import annotations

import os

import streamlit as st
from streamlit_autorefresh import st_autorefresh

from lakeaudit.dashboard.panels import (
    agent_loop_visualizer,
    catalog_filter,
    cost_meter,
    document_stream,
    quality_metrics,
    side_by_side_eval,
)

RUN_ID = os.environ.get("LAKEAUDIT_RUN_ID", "default")

st.set_page_config(page_title="LakeAudit", layout="wide")

# 1Hz refresh for streams + counters. Visualizer panel uses 250ms internally.
st_autorefresh(interval=1000, key="dashboard_1hz")

# Header — config summary + positioning one-liner from PRD §3.
st.title("LakeAudit")
st.caption(
    f"Run: {RUN_ID}   "
    f"·   N=3 proposers   ·   K=10 trace sampling   ·   ceiling=$30"
)
st.markdown(
    "_\"Scale AI labels data. LakeAudit makes university data labelable in the first place.\"_"
)

# Row 1: document stream + agent loop visualizer
col_a, col_b = st.columns(2)
with col_a:
    document_stream.render(RUN_ID)
with col_b:
    agent_loop_visualizer.render(RUN_ID)

# Row 2: quality metrics + cost meter
col_c, col_d = st.columns(2)
with col_c:
    quality_metrics.render(RUN_ID)
with col_d:
    cost_meter.render(RUN_ID)

# Row 3: catalog filter + side-by-side eval
col_e, col_f = st.columns(2)
with col_e:
    catalog_filter.render(RUN_ID)
with col_f:
    side_by_side_eval.render(RUN_ID)
