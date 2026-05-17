"""Golden end-to-end: 5 fixture docs through the loop with MockInferenceClient.

Asserts the contracted shape of what lands in SQLite: 5 catalog records, 5 label
payloads, ~55 trace events, JSONL export matches fixture.

No live Wafer/OpenAI calls — runs in CI in <30s.
See docs/08-ops-and-demo.md §Testing strategy.
"""

from __future__ import annotations

import pytest


@pytest.mark.skip(reason="Awaits ingest+loop+storage+export wired together.")
async def test_golden_five_docs_endtoend(tmp_path, fixtures_dir) -> None:
    """ingest → run → export pipeline on 5 fixture PDFs."""
    ...
