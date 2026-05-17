"""Panel 2: Agent loop visualizer — render the propose → critique → refine → vote → enrich tree.

Refresh: 250ms (faster than the rest). Picks a verbose-traced doc (every Kth, K=10)
and animates its trace_events tree. Hover shows prompt/response.
See docs/06-dashboard.md §Panel 2 and docs/02-agent-loop.md §Trace contract.
"""

from __future__ import annotations

import streamlit as st
from streamlit_autorefresh import st_autorefresh

from datalake.dashboard._db import read, read_one
from datalake.dashboard.queries import PICK_VERBOSE_TRACED_DOC, TRACE_FOR_DOC

_STATUS_COLOR = {
    "OK": "#4caf50",
    "FAILED": "#e53935",
    "TIMEOUT": "#fb8c00",
    None: "#9e9e9e",
}


def _build_dot(rows: list) -> str:
    """Render a trace event list into a Graphviz tree."""
    lines = [
        "digraph trace {",
        '  rankdir=LR;',
        '  node [shape=box, style=filled, fontname="Helvetica", fontsize=10];',
    ]
    by_id: dict[str, dict] = {r["id"]: dict(r) for r in rows}
    for ev_id, ev in by_id.items():
        label = ev["pass"]
        if ev["proposal_idx"] is not None:
            label += f"#{ev['proposal_idx']}"
        latency_ms = ""
        if ev["started_at"] and ev["ended_at"]:
            latency_ms = f"\\n{int((ev['ended_at'] - ev['started_at']) * 1000)}ms"
        color = _STATUS_COLOR.get(ev["status"], "#9e9e9e")
        lines.append(
            f'  "{ev_id}" [label="{label}{latency_ms}", fillcolor="{color}", fontcolor="white"];'
        )
    for ev_id, ev in by_id.items():
        parent = ev.get("parent_event_id")
        if parent and parent in by_id:
            lines.append(f'  "{parent}" -> "{ev_id}";')
    lines.append("}")
    return "\n".join(lines)


def render(run_id: str) -> None:
    st.subheader("2. Agent loop visualizer")
    st_autorefresh(interval=250, key="visualizer_4hz")

    doc = read_one(PICK_VERBOSE_TRACED_DOC, run_id=run_id)
    if not doc:
        st.caption("No verbose-traced docs yet. Visualizer activates once the first K=10 doc completes a PROPOSE pass.")
        return

    doc_id = doc["id"]
    st.caption(f"Sampled doc: `{doc_id[:8]}…`")
    events = read(TRACE_FOR_DOC, doc_id=doc_id)
    if not events:
        st.caption("Doc selected but no trace events yet.")
        return

    st.graphviz_chart(_build_dot(events), use_container_width=True)
