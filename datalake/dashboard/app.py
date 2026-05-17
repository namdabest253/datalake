"""Streamlit entrypoint. Single page, six panels + an export-artifacts strip.

Run: `streamlit run datalake/dashboard/app.py` (or `datalake dashboard`).
See docs/06-dashboard.md §Page layout.
"""

from __future__ import annotations

import os

import streamlit as st
from streamlit_autorefresh import st_autorefresh

from datalake.dashboard._db import read_one
from datalake.dashboard.panels import (
    agent_loop_visualizer,
    catalog_filter,
    cost_meter,
    document_stream,
    export_artifacts,
    quality_metrics,
    side_by_side_eval,
)


def _resolve_run_id() -> str | None:
    """DATALAKE_RUN_ID env wins; else fall back to the most-recent run in the DB."""
    env_val = os.environ.get("DATALAKE_RUN_ID")
    if env_val and env_val != "default":
        return env_val
    row = read_one("SELECT id FROM runs ORDER BY started_at DESC LIMIT 1")
    return row["id"] if row else None


RUN_ID = _resolve_run_id()

st.set_page_config(page_title="Datalake", layout="wide")

# 1Hz refresh for streams + counters. Visualizer panel uses 250ms internally.
st_autorefresh(interval=1000, key="dashboard_1hz")

# Header — config summary + positioning one-liner from PRD §3.
st.title("Datalake")
if RUN_ID is None:
    st.error(
        "No runs found in the DB. Run `datalake ingest <path>` then `datalake run` first."
    )
    st.stop()

st.caption(
    f"Run: `{RUN_ID}`   "
    f"·   N=3 proposers   ·   K=10 trace sampling   ·   ceiling=$30"
)
st.markdown(
    "_\"Scale AI labels data. Datalake makes university data labelable in the first place.\"_"
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

# Row 4: export artifacts (full-width strip so download buttons get room)
export_artifacts.render(RUN_ID)
