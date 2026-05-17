"""Panel 1: Document stream — docs/sec counter + latest 20 finalized records.

Refresh: 1Hz. Query: datalake.dashboard.queries.LATEST_RECORDS + DOCS_PER_SEC_COUNTER.
See docs/06-dashboard.md §Panel 1.
"""

from __future__ import annotations

import json
import time

import streamlit as st

from datalake.dashboard._db import read, read_one
from datalake.dashboard.queries import DOCS_PER_SEC_COUNTER, LATEST_RECORDS


def _docs_per_sec(run_id: str, docs_done: int) -> float:
    """Compute docs/sec from delta since previous poll. Uses st.session_state."""
    key_n = f"_ds_prev_n_{run_id}"
    key_t = f"_ds_prev_t_{run_id}"
    now = time.time()
    prev_n = st.session_state.get(key_n)
    prev_t = st.session_state.get(key_t)
    st.session_state[key_n] = docs_done
    st.session_state[key_t] = now
    if prev_n is None or prev_t is None or now - prev_t < 0.1:
        return 0.0
    return max(0.0, (docs_done - prev_n) / (now - prev_t))


def render(run_id: str) -> None:
    st.subheader("1. Document stream")

    counter = read_one(DOCS_PER_SEC_COUNTER, run_id=run_id)
    docs_done = int(counter["docs_done"]) if counter else 0
    dps = _docs_per_sec(run_id, docs_done)

    c1, c2 = st.columns(2)
    c1.metric("docs/sec", f"{dps:.1f}")
    c2.metric("total processed", f"{docs_done:,}")

    rows = read(LATEST_RECORDS, run_id=run_id)
    if not rows:
        st.caption("Waiting for the loop to finalize the first document…")
        return

    table = []
    for r in rows:
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
