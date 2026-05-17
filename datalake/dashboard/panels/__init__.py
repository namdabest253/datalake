"""One file per dashboard panel. See docs/06-dashboard.md §Per-panel data source.

Each panel exposes a `render(run_id: str) -> None` function called by app.py.
"""

from . import (  # noqa: F401
    agent_loop_visualizer,
    catalog_filter,
    cost_meter,
    document_stream,
    export_artifacts,
    quality_metrics,
    side_by_side_eval,
)
