"""Panel 4: Cost meter — 3-row foil (Wafer / GPT-4 / human labeler) + ratios.

The three-foil comparison is the core competitive claim from PRD §3. Wafer beats
GPT-4 by ~500× and beats Surge-tier human labeling by ~30,000–100,000×.

Refresh: 1Hz. See docs/06-dashboard.md §Panel 4.
"""

from __future__ import annotations

import streamlit as st

from datalake.dashboard._db import read_one
from datalake.dashboard.queries import COST_METER

FOIL_METHODOLOGY_ANNOTATION = (
    "Foils estimated, no real spend. "
    "GPT-4: tokens × public pricing. "
    "Human: $50/paper midpoint (Surge/Scale, PRD §3). "
    "GPT-4 actually runs only on the 200-doc eval subset; no human labels are produced."
)


def _fmt_usd(micro_usd: int) -> str:
    """Format micro-USD into $X.XX / $X.XK / $X.XM."""
    usd = micro_usd / 1_000_000
    if usd >= 1_000_000:
        return f"${usd / 1_000_000:.2f}M"
    if usd >= 1_000:
        return f"${usd / 1_000:.2f}K"
    return f"${usd:.2f}"


def render(run_id: str) -> None:
    st.subheader("4. Cost meter")

    row = read_one(COST_METER, run_id=run_id)
    wafer = int(row["total_wafer_micro_usd"]) if row else 0
    gpt4 = int(row["total_gpt4_equivalent_micro_usd"]) if row else 0
    human = int(row["total_human_labeler_equivalent_micro_usd"]) if row else 0

    c1, c2, c3 = st.columns(3)
    c1.metric("Wafer (actual)", _fmt_usd(wafer))
    c2.metric("GPT-4 (foil)", _fmt_usd(gpt4))
    c3.metric("Human labeler (foil)", _fmt_usd(human))

    if wafer > 0:
        vs_gpt = gpt4 / wafer if gpt4 else 0
        vs_human = human / wafer if human else 0
        st.markdown(
            f"**vs GPT-4:** {vs_gpt:,.0f}× cheaper   ·   "
            f"**vs human:** {vs_human:,.0f}× cheaper"
        )
    else:
        st.caption("Ratios appear once Wafer spending begins.")

    st.markdown(
        f"<small><i style='color:#888'>ⓘ {FOIL_METHODOLOGY_ANNOTATION}</i></small>",
        unsafe_allow_html=True,
    )
