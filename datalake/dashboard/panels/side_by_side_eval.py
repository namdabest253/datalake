"""Panel 6: Side-by-side eval — Datalake win rate + per-dimension deltas vs GPT-4.

Populated by `datalake eval`. No auto-refresh (data only changes when eval runs).
See docs/06-dashboard.md §Panel 6 and docs/07-evaluation.md.
"""

from __future__ import annotations

import streamlit as st


def render(run_id: str) -> None:
    st.subheader("6. Side-by-side eval (Datalake vs GPT-4)")
    raise NotImplementedError(
        "TODO: query EVAL_RESULTS, unblind with datalake.eval.scoring.resolve_winner, "
        "compute compute_win_rate + compute_dimension_deltas, render. "
        "Target: ≥65% win rate, cost ratio ≤ 0.3 per PRD §9."
    )
