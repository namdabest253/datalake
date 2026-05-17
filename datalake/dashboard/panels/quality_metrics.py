"""Panel 3: Quality metrics — avg confidence, low-conf flag rate, inter-agent agreement.

Refresh: 1Hz. See docs/06-dashboard.md §Panel 3.
"""

from __future__ import annotations

import streamlit as st

from datalake.dashboard._db import read_one
from datalake.dashboard.queries import LOW_CONF_FLAG_RATE, QUALITY_COUNTERS

INTER_AGENT_AGREEMENT_SQL = """
WITH per_doc AS (
    SELECT t.doc_id,
           COUNT(DISTINCT t.id) AS n_proposals
    FROM trace_events t
    JOIN documents d ON d.id = t.doc_id
    WHERE d.run_id = :run_id
      AND t.pass = 'PROPOSE'
      AND t.proposal_idx IS NOT NULL
      AND t.status = 'OK'
    GROUP BY t.doc_id
)
SELECT
    AVG(CASE WHEN n_proposals >= 2 THEN 1.0 ELSE 0.0 END) AS agreement_pct
FROM per_doc
"""


def render(run_id: str) -> None:
    st.subheader("3. Quality metrics")

    counters = read_one(QUALITY_COUNTERS, run_id=run_id)
    low_conf = read_one(LOW_CONF_FLAG_RATE, run_id=run_id)
    agreement = read_one(INTER_AGENT_AGREEMENT_SQL, run_id=run_id)

    avg_conf = float(counters["avg_overall_confidence"]) if counters else 0.0
    docs_done = int(counters["docs_done"]) if counters else 0
    docs_partial = int(counters["docs_partial"]) if counters else 0
    docs_failed = int(counters["docs_failed"]) if counters else 0
    low_pct = float(low_conf["low_conf_pct"] or 0.0) if low_conf else 0.0
    agree_pct = float(agreement["agreement_pct"] or 0.0) if agreement else 0.0

    c1, c2, c3 = st.columns(3)
    c1.metric("avg confidence", f"{avg_conf:.2f}")
    c2.metric("low-conf flag %", f"{low_pct * 100:.1f}%")
    c3.metric("inter-agent agreement", f"{agree_pct:.2f}")

    st.caption(
        f"docs done: {docs_done:,}   ·   partial: {docs_partial:,}   ·   failed: {docs_failed:,}"
    )
    if docs_done == 0:
        st.caption("Counters populate as the loop completes documents.")
