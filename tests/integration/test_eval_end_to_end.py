"""End-to-end integration test for `datalake eval`.

Stubs both the baseline Wafer client and the judge client, seeds a tiny DB with
real catalog + label rows from a fake prior `datalake run`, then exercises
`harness.run_eval` and asserts:
  - eval_pairs has 4 rows (one per held-out doc).
  - eval_results has 4 rows.
  - inference_calls has the expected wafer + openai (estimated) foil rows.
  - The JSON report file is written with the expected shape.

See docs/07-evaluation.md.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from datalake.config import Paths, Settings
from datalake.eval import harness
from datalake.inference.base import CallResult
from datalake.storage.db import (
    connect,
    init_db,
    insert_catalog_record,
    insert_document,
    insert_label_payload,
    insert_run,
)
from datalake.storage.models import CatalogRecord, LabelPayload

# ---------------------------------------------------------------------------
# Stub clients
# ---------------------------------------------------------------------------


def _baseline_payload() -> dict:
    """Valid BaselineRecord JSON — intentionally weaker than the loop output."""
    return {
        "catalog": {
            "content_type": "research_paper",
            "content_type_confidence": 0.6,
            "ownership": "unclear",
            "ownership_confidence": 0.5,
            "ownership_rationale": "Looks like a paper.",
            "compliance_flags": ["unclear"],
            "commercial_score": 50,
            "commercial_action": "needs_consent",
        },
        "label": {
            "structured_abstract": {
                "problem": "x", "approach": "y", "findings": "z", "limitations": "w",
            },
            "methodology_named": [],
            "methodology_other_freetext": "deep learning",
            "novelty_claim": "A new method.",
            "evidence_type": "empirical",
            "evidence_strength": "moderate",
            "sample_size": None,
            "claim_graph": [],
            "citations": [],
            "domain_tags": ["ml"],
        },
        "enriched": {
            "expanded_abstract": "blah",
            "novelty_rationale": "blah",
            "citation_context": [],
            "claim_graph_v2": [],
            "derived_keywords": [],
            "suggested_buyer_segments": ["frontier_lab"],
        },
        "overall_confidence": 0.5,
    }


class _StubBaselineClient:
    """Returns a fixed weak BaselineRecord on every call. Looks like WaferClient."""

    def __init__(self) -> None:
        self.model = "qwen-3.5-397b"
        self.calls = 0

    async def call(
        self,
        system: str,
        user: str,
        *,
        json_schema: dict | None = None,
        temperature: float = 0.5,
        timeout: float = 20.0,
    ) -> CallResult:
        self.calls += 1
        return CallResult(
            response_text=json.dumps(_baseline_payload()),
            tokens_in=2000,
            tokens_out=400,
            cost_micro_usd=420,  # ~$0.00042 — placeholder
            cost_basis="actual",
            latency_ms=10,
            model=self.model,
            provider="wafer",
        )


class _StubJudgeClient:
    """Always picks A as the winner with a big methodology delta. Looks like JudgeClient."""

    def __init__(self) -> None:
        self.model = "qwen-3.5-strong"
        self.calls = 0

    async def call(
        self,
        system: str,
        user: str,
        *,
        json_schema: dict | None = None,
        temperature: float = 0.0,
        timeout: float = 20.0,
    ) -> CallResult:
        self.calls += 1
        payload = {
            "winner": "A",
            "a_scores": {
                "methodology_specificity": 5,
                "novelty_claim_accuracy": 5,
                "evidence_quality": 4,
                "citation_completeness": 4,
                "compliance_correctness": 5,
                "ownership_defensibility": 5,
            },
            "b_scores": {
                "methodology_specificity": 2,
                "novelty_claim_accuracy": 3,
                "evidence_quality": 3,
                "citation_completeness": 2,
                "compliance_correctness": 2,
                "ownership_defensibility": 2,
            },
            "rationale": "A names specific techniques; B is generic.",
        }
        return CallResult(
            response_text=json.dumps(payload),
            tokens_in=1500,
            tokens_out=200,
            cost_micro_usd=600,
            cost_basis="actual",
            latency_ms=10,
            model=self.model,
            provider="judge",
        )


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


async def _seed_db(db_path: Path, n_docs: int = 4) -> str:
    """Insert a run + N DONE documents with catalog + label rows."""
    await init_db(db_path, persist=False)
    async with connect(db_path) as conn:
        run_id = "prior-run"
        await insert_run(conn, run_id, "commit", "corpus-v1", "{}", '{"wafer": "qwen-3.5-397b"}')
        for i in range(n_docs):
            doc_id = f"doc-{i}"
            await insert_document(
                conn, doc_id, run_id, source_path=f"/sample-{i}.pdf",
                source_hash=f"sha:{i}", content_type_guess="research_paper",
            )
            # Bump to DONE so the harness's sampling SQL picks it up.
            await conn.execute(
                "UPDATE documents SET status='DONE' WHERE id=?", (doc_id,)
            )
            await insert_catalog_record(conn, CatalogRecord(
                doc_id=doc_id,
                content_type="research_paper",
                content_type_confidence=0.95,
                ownership="joint",
                ownership_confidence=0.85,
                ownership_rationale="UofC + NSF grant + CC-BY license",
                compliance_flags=["clean", "public_domain"],
                commercial_score=88,
                commercial_action="license_ready",
            ))
            await insert_label_payload(conn, LabelPayload(
                doc_id=doc_id,
                structured_abstract={
                    "problem": "p", "approach": "a", "findings": "f", "limitations": "l",
                },
                methodology={
                    "named": ["contrastive_learning", "fine_tuned_bert"],
                    "other_freetext": "triplet loss",
                },
                novelty_claim=f"Specific novelty claim #{i} with grounded evidence.",
                evidence_quality={"type": "empirical", "strength": "strong", "sample_size": 12000},
                claim_graph=[{"claim": "x", "evidence_pointer": "Table 2"}],
                citations=[],
                domain_tags=["ml", "nlp"],
                enriched_payload={
                    "expanded_abstract": "Detailed expanded abstract.",
                    "novelty_rationale": "Detailed novelty rationale.",
                    "citation_context": [],
                    "claim_graph_v2": [],
                    "derived_keywords": ["contrastive", "retrieval"],
                    "suggested_buyer_segments": ["frontier_lab"],
                },
            ))
        await conn.commit()
    return run_id


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_eval_end_to_end(tmp_path: Path, monkeypatch) -> None:
    # Stub _parse_one so the harness doesn't try to open real PDFs.
    def _fake_parse(path: Path) -> tuple[str, list[dict]]:
        return (f"Sample document text for {path.name}.", [])

    monkeypatch.setattr("datalake.ingest.parser._parse_one", _fake_parse)

    db_path = tmp_path / "lakeaudit.db"
    await _seed_db(db_path, n_docs=4)

    settings = Settings(
        wafer_api_key="dummy",
        judge_api_key="dummy",
        paths=Paths(sqlite_db=db_path, heuristics=Path("datalake/prompts/heuristics.yaml")),
    )

    baseline = _StubBaselineClient()
    judge = _StubJudgeClient()

    eval_run_id = "eval-1"
    report = await harness.run_eval(
        n=4,
        run_id=eval_run_id,
        settings=settings,
        baseline_client=baseline,
        judge=judge,
        heuristics_yaml="",
        dry_run=False,
        seed=42,
    )

    # 4 baseline calls + 1 self-test + 4 judge calls = stub call counts.
    assert baseline.calls == 4
    assert judge.calls == 5  # 1 self-test + 4 eval pairs

    # Report shape + values.
    assert report["n_pairs"] == 4
    # Judge always picks A. With a_is_datalake randomized, win_rate computed
    # by unblinding should still be near 1.0 because A=Datalake roughly half
    # the time and B=Datalake half the time — but the judge only ever picks A.
    # So win_rate equals the fraction of pairs where a_is_datalake is True.
    assert 0.0 <= report["win_rate"] <= 1.0
    assert report["cost_ratio"] > 0
    assert "methodology_specificity" in report["dimension_deltas"]
    assert report["judge_model"] == settings.judge_model
    assert report["loop_model"] == settings.wafer_loop_model
    assert report["baseline_model"] == settings.baseline_model

    # Report file is written to ./.datalake/eval_report_<run_id>.json.
    out_path = Path("./.datalake") / f"eval_report_{eval_run_id}.json"
    try:
        assert out_path.exists()
        on_disk = json.loads(out_path.read_text())
        assert on_disk["n_pairs"] == 4
    finally:
        if out_path.exists():
            out_path.unlink()

    # DB rows: 4 eval_pairs, 4 eval_results.
    async with connect(db_path) as conn:
        n_pairs = (await (await conn.execute(
            "SELECT COUNT(*) FROM eval_pairs WHERE run_id=?", (eval_run_id,)
        )).fetchone())[0]
        assert n_pairs == 4

        n_results = (await (await conn.execute(
            "SELECT COUNT(*) FROM eval_results r JOIN eval_pairs p ON r.pair_id=p.id "
            "WHERE p.run_id=?", (eval_run_id,)
        )).fetchone())[0]
        assert n_results == 4

        # Each baseline call writes TWO inference_calls rows (wafer actual + openai estimated).
        by_kind = await (await conn.execute(
            "SELECT provider, cost_basis, COUNT(*) FROM inference_calls "
            "WHERE run_id=? GROUP BY provider, cost_basis",
            (eval_run_id,),
        )).fetchall()
        counts = {(r[0], r[1]): r[2] for r in by_kind}
        assert counts.get(("wafer", "actual")) == 4
        assert counts.get(("openai", "estimated")) == 4

        # dimension_scores JSON has A/B keys (dashboard reads them).
        ds_row = await (await conn.execute(
            "SELECT dimension_scores FROM eval_results LIMIT 1"
        )).fetchone()
        scores = json.loads(ds_row[0])
        assert "methodology_specificity" in scores
        assert set(scores["methodology_specificity"].keys()) == {"A", "B"}


@pytest.mark.asyncio
async def test_eval_aborts_if_judge_self_test_fails(tmp_path: Path, monkeypatch) -> None:
    """If the judge mis-calls the canonical pair, the whole eval run aborts."""
    def _fake_parse(path: Path) -> tuple[str, list[dict]]:
        return ("doc body", [])

    monkeypatch.setattr("datalake.ingest.parser._parse_one", _fake_parse)

    db_path = tmp_path / "lakeaudit.db"
    await _seed_db(db_path, n_docs=2)
    settings = Settings(
        wafer_api_key="dummy",
        judge_api_key="dummy",
        paths=Paths(sqlite_db=db_path, heuristics=Path("datalake/prompts/heuristics.yaml")),
    )

    class _BrokenJudge:
        """Always picks B — fails the self-test."""
        model = "broken"

        async def call(self, system, user, *, json_schema=None, temperature=0.0, timeout=20.0):
            payload = {
                "winner": "B",
                "a_scores": {d: 2 for d in [
                    "methodology_specificity", "novelty_claim_accuracy",
                    "evidence_quality", "citation_completeness",
                    "compliance_correctness", "ownership_defensibility",
                ]},
                "b_scores": {d: 5 for d in [
                    "methodology_specificity", "novelty_claim_accuracy",
                    "evidence_quality", "citation_completeness",
                    "compliance_correctness", "ownership_defensibility",
                ]},
                "rationale": "Wrong call.",
            }
            return CallResult(
                response_text=json.dumps(payload),
                tokens_in=10, tokens_out=10, cost_micro_usd=1, cost_basis="actual",
                latency_ms=1, model="broken", provider="judge",
            )

    with pytest.raises(RuntimeError, match="self-test FAILED"):
        await harness.run_eval(
            n=2,
            run_id="eval-broken",
            settings=settings,
            baseline_client=_StubBaselineClient(),
            judge=_BrokenJudge(),
            heuristics_yaml="",
            dry_run=True,
            seed=1,
        )
