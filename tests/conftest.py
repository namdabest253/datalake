"""Shared pytest fixtures.

See docs/08-ops-and-demo.md §Testing strategy.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from lakeaudit.inference.base import CallResult, InferenceClient


class MockInferenceClient:
    """Deterministic InferenceClient for unit + integration tests.

    No network. Configure responses by injecting a mapping at construction.
    """

    def __init__(self, responses: dict[str, str] | None = None) -> None:
        self.responses = responses or {}
        self.calls: list[dict] = []

    async def call(
        self,
        system: str,
        user: str,
        *,
        json_schema: dict | None = None,
        temperature: float = 0.5,
        timeout: float = 20.0,
    ) -> CallResult:
        self.calls.append({"system": system, "user": user, "temperature": temperature})
        # Look up canned response by a key the test provides via system message tag.
        key = system.split("|", 1)[0].strip() if "|" in system else "default"
        response = self.responses.get(key, "{}")
        return CallResult(
            response_text=response,
            tokens_in=len(user) // 4,
            tokens_out=len(response) // 4,
            cost_micro_usd=100,
            cost_basis="actual",
            latency_ms=10,
            model="mock",
            provider="mock",
        )


@pytest.fixture
def mock_client() -> InferenceClient:
    """A baseline mock with no canned responses — tests inject their own."""
    return MockInferenceClient()


@pytest.fixture
def fixtures_dir() -> Path:
    return Path(__file__).parent / "fixtures"
