"""Panel 4: Cost meter — 3-row foil (Wafer / GPT-4 / human labeler) + ratios.

The three-foil comparison is the core competitive claim from PRD §3. Wafer beats
GPT-4 by ~500× and beats Surge-tier human labeling by ~30,000–100,000×.

Refresh: 1Hz. See docs/06-dashboard.md §Panel 4.
"""

from __future__ import annotations

import streamlit as st

FOIL_METHODOLOGY_ANNOTATION = (
    "Foils estimated, no real spend. "
    "GPT-4: tokens × public pricing. "
    "Human: $50/paper midpoint (Surge/Scale, PRD §3). "
    "GPT-4 actually runs only on the 200-doc eval subset; no human labels are produced."
)


def render(run_id: str) -> None:
    st.subheader("4. Cost meter")
    raise NotImplementedError(
        "TODO: query COST_METER, render the three USD numbers (abbreviating $1.8K/$437K/$1.2M), "
        "show ratios `vs GPT-4` and `vs human`, then ALWAYS render "
        "FOIL_METHODOLOGY_ANNOTATION below in small italic gray text. "
        "The annotation is non-negotiable and not user-dismissable."
    )
