"""State machine driven with the mocked InferenceClient.

See docs/02-agent-loop.md §State machine, §Partial-failure policy.
"""

from __future__ import annotations

import pytest


@pytest.mark.skip(reason="Awaits lakeaudit.loop.state_machine.run_doc implementation.")
async def test_happy_path_three_proposers_succeed() -> None:
    """All 3 proposers succeed → DONE with full label payload."""
    ...


@pytest.mark.skip(reason="Awaits lakeaudit.loop.state_machine.run_doc implementation.")
async def test_one_proposer_fails_continues_with_two() -> None:
    """1 of 3 proposers fails → continue with 2 → DONE."""
    ...


@pytest.mark.skip(reason="Awaits lakeaudit.loop.state_machine.run_doc implementation.")
async def test_two_proposers_fail_marks_failed() -> None:
    """≥2 of 3 proposers fail → doc → FAILED."""
    ...


@pytest.mark.skip(reason="Awaits lakeaudit.loop.state_machine.run_doc implementation.")
async def test_enrich_failure_emits_partial() -> None:
    """Enrich fails → catalog-only emit with partial=True."""
    ...


@pytest.mark.skip(reason="Awaits lakeaudit.loop.state_machine.run_doc implementation.")
async def test_per_doc_budget_timeout() -> None:
    """30s wall-clock exceeded → cancel in-flight, emit what completed, timeout=True."""
    ...
