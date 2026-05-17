"""End-to-end happy path through the 6-pass loop with a smart mock client.

Verifies:
  - All 11 expected inference calls fire (3 propose + 3 critique + 3 refine + 1 vote + 1 enrich).
  - Document ends in DONE state, non-partial, non-timeout.
  - Trace events (11) and inference_calls rows (22 — 11 actual + 11 GPT-4 foils) written.
  - Catalog + label rows materialised correctly.
  - Dashboard counters reflect docs_done=1, costs, and the winning vote confidence.

See docs/02-agent-loop.md §State machine and §Partial-failure policy.
"""

from __future__ import annotations

import asyncio
import json
import time
from pathlib import Path

from datalake.config import Settings
from datalake.inference.base import CallResult
from datalake.loop.state_machine import State, run_doc
from datalake.storage.db import connect, init_db, insert_document, insert_run
from datalake.storage.models import Document


def _proposal_payload() -> dict:
    return {
        "catalog": {
            "content_type": "research_paper",
            "content_type_confidence": 0.9,
            "ownership": "institution",
            "ownership_confidence": 0.85,
            "ownership_rationale": "UofC affiliation + NSF grant",
            "compliance_flags": ["clean"],
            "commercial_score": 80,
            "commercial_action": "license_ready",
        },
        "label": {
            "structured_abstract": {"problem": "x", "approach": "y", "findings": "z", "limitations": "w"},
            "methodology_named": ["fine_tuned_bert"],
            "methodology_other_freetext": None,
            "novelty_claim": "novel contrastive approach",
            "evidence_type": "empirical",
            "evidence_strength": "strong",
            "sample_size": 1000,
            "claim_graph": [],
            "citations": [],
            "domain_tags": ["ml"],
        },
        "overall_confidence": 0.85,
    }


def _canned_response_for(schema_props: dict) -> dict:
    """Return a valid response payload keyed off distinctive schema field names."""
    if "winner_idx" in schema_props:
        return {"winner_idx": 0, "winner_confidence": 0.92, "rationale": "best", "runners_up": [1, 2]}
    if "field_critiques" in schema_props:
        return {"proposal_idx": 0, "field_critiques": [], "overall_assessment": "accept", "rationale": "good"}
    if "expanded_abstract" in schema_props:
        return {
            "expanded_abstract": "X",
            "novelty_rationale": "Y",
            "citation_context": [],
            "claim_graph_v2": [],
            "derived_keywords": [],
            "suggested_buyer_segments": ["frontier_lab"],
        }
    if "revision_summary" in schema_props:
        return _proposal_payload() | {"revision_summary": "applied critique"}
    return _proposal_payload()  # ProposalRecord


class _SmartMockClient:
    """Returns valid JSON matching whichever pydantic schema the call advertises."""

    def __init__(self) -> None:
        self.calls: list[set[str]] = []

    async def call(
        self,
        system: str,
        user: str,
        *,
        json_schema: dict | None = None,
        temperature: float = 0.5,
        timeout: float = 20.0,
    ) -> CallResult:
        props = json_schema.get("properties", {}) if json_schema else {}
        self.calls.append(set(props.keys()))
        response = json.dumps(_canned_response_for(props))
        return CallResult(
            response_text=response,
            tokens_in=100,
            tokens_out=50,
            cost_micro_usd=140,
            cost_basis="actual",
            latency_ms=20,
            model="qwen-3.5-397b",
            provider="wafer",
        )


async def test_happy_path(tmp_path: Path) -> None:
    settings = Settings(
        wafer_api_key="dummy",
        judge_api_key="dummy",
        n_proposers=3,
        per_doc_budget_seconds=30,
        wafer_spend_ceiling_usd=1000,
    )
    db = tmp_path / "loop.db"
    await init_db(db, persist=False)
    client = _SmartMockClient()
    per_doc_sem = asyncio.Semaphore(8)
    run_id = "test-happy-path"

    async with connect(db) as conn:
        await insert_run(conn, run_id, "commit", "corpus-v1", "{}", '{"wafer": "mock"}')
        doc = Document(
            id="doc-1",
            run_id=run_id,
            source_path="/sample.pdf",
            source_hash="sha:x",
            content_type_guess="research_paper",
            ingested_at=time.time(),
            status="INGESTED",
            text="Sample paper text about contrastive learning.",
            references=[],
        )
        await insert_document(conn, doc.id, run_id, doc.source_path, doc.source_hash, doc.content_type_guess)
        await conn.commit()

        result = await run_doc(
            doc, 0, client, "heuristics: ...", settings, per_doc_sem, conn=conn, run_id=run_id
        )

        # Loop outcome
        assert result.state == State.DONE
        assert not result.partial and not result.timeout and not result.vote_degraded
        assert len(result.proposals) == 3
        assert len(result.critiques) == 3
        assert len(result.refined) == 3
        assert result.vote is not None and result.vote.winner_idx == 0
        assert result.enriched is not None
        assert result.wafer_micro_usd > 0 and result.gpt4_micro_usd > result.wafer_micro_usd

        # Exactly 11 inference calls (3+3+3+1+1)
        assert len(client.calls) == 11

        # DB state
        row = await (await conn.execute(
            "SELECT status, partial FROM documents WHERE id=?", ("doc-1",)
        )).fetchone()
        assert tuple(row) == ("DONE", 0)

        traces = await (await conn.execute(
            "SELECT COUNT(*) FROM trace_events WHERE doc_id=?", ("doc-1",)
        )).fetchone()
        assert traces[0] == 11

        # 22 inference_calls: 11 actual Wafer + 11 estimated GPT-4 foils.
        calls = await (await conn.execute(
            "SELECT COUNT(*), provider, cost_basis FROM inference_calls "
            "WHERE doc_id=? GROUP BY provider, cost_basis ORDER BY provider, cost_basis",
            ("doc-1",),
        )).fetchall()
        by_kind = {(r[1], r[2]): r[0] for r in calls}
        assert by_kind == {("openai", "estimated"): 11, ("wafer", "actual"): 11}

        # Catalog + label rows landed.
        catalog = await (await conn.execute(
            "SELECT content_type, commercial_action FROM catalog_records WHERE doc_id=?",
            ("doc-1",),
        )).fetchone()
        assert tuple(catalog) == ("research_paper", "license_ready")
        label = await (await conn.execute(
            "SELECT novelty_claim, partial FROM label_payloads WHERE doc_id=?", ("doc-1",)
        )).fetchone()
        assert label[0] == "novel contrastive approach"
        assert label[1] == 0

        # Dashboard counters: docs_done=1, avg_conf=0.92 (from vote.winner_confidence),
        # all three foils populated.
        counters = await (await conn.execute(
            "SELECT docs_done, docs_partial, docs_failed, total_wafer_micro_usd, "
            "total_gpt4_equivalent_micro_usd, total_human_labeler_equivalent_micro_usd, "
            "avg_overall_confidence FROM dashboard_counters WHERE run_id=?",
            (run_id,),
        )).fetchone()
        assert counters[0] == 1  # docs_done
        assert counters[1] == 0  # docs_partial
        assert counters[2] == 0  # docs_failed
        assert counters[3] == result.wafer_micro_usd
        assert counters[4] == result.gpt4_micro_usd
        assert counters[5] == 50_000_000  # $50 Surge rate × 1 research_paper
        assert abs(counters[6] - 0.92) < 0.001


