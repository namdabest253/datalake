"""Panel 6: Side-by-side eval — Datalake win rate + per-dimension deltas vs GPT-4.

Populated by `datalake eval`. No auto-refresh (data only changes when eval runs).
See docs/06-dashboard.md §Panel 6 and docs/07-evaluation.md.
"""

from __future__ import annotations

import json
from statistics import mean

import streamlit as st

from datalake.dashboard._db import read
from datalake.dashboard.queries import EVAL_RESULTS


def _resolve_winner(a_is_datalake: bool, winner: str) -> str:
    """Map the blinded winner letter back to the pipeline name."""
    if winner == "tie":
        return "tie"
    if winner == "A":
        return "datalake" if a_is_datalake else "gpt4"
    if winner == "B":
        return "gpt4" if a_is_datalake else "datalake"
    return "tie"


def render(run_id: str) -> None:
    st.subheader("6. Side-by-side eval (Datalake vs GPT-4)")

    rows = read(EVAL_RESULTS, run_id=run_id)
    if not rows:
        st.caption("Run `datalake eval --n 200` to populate this panel.")
        return

    decided = [r for r in rows if r["winner"] != "tie"]
    winners = [_resolve_winner(bool(r["a_is_datalake"]), r["winner"]) for r in decided]
    n_total = len(rows)
    n_dl_wins = sum(1 for w in winners if w == "datalake")
    win_rate = n_dl_wins / len(winners) if winners else 0.0

    c1, c2 = st.columns(2)
    c1.metric("win rate (decided)", f"{win_rate * 100:.1f}%")
    c2.metric("pairs judged", f"{n_total:,}")

    # Per-dimension deltas (Datalake − GPT-4) averaged across pairs.
    dim_deltas: dict[str, list[float]] = {}
    for r in rows:
        try:
            scores = json.loads(r["dimension_scores"]) or {}
        except (TypeError, json.JSONDecodeError):
            continue
        is_dl_a = bool(r["a_is_datalake"])
        for dim, pair in scores.items():
            if not isinstance(pair, dict):
                continue
            a, b = float(pair.get("A", 0)), float(pair.get("B", 0))
            delta = (a - b) if is_dl_a else (b - a)
            dim_deltas.setdefault(dim, []).append(delta)

    if dim_deltas:
        st.markdown("**Per-dimension deltas (Datalake − GPT-4)**")
        table = [
            {"dimension": dim, "delta": round(mean(vals), 2), "n": len(vals)}
            for dim, vals in sorted(dim_deltas.items())
        ]
        st.dataframe(table, hide_index=True, use_container_width=True)

    if win_rate >= 0.65:
        st.success(f"Above PRD §9 target of 65% win rate.")
    else:
        st.warning(f"Below PRD §9 target of 65% win rate.")
