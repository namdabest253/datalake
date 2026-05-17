"""Per-doc orchestrator: READ → PROPOSE×N → CRITIQUE×N → REFINE×N → VOTE → ENRICH.

See docs/02-agent-loop.md §State machine, §Partial-failure policy, §Cancellation & budget.
"""

from __future__ import annotations

import asyncio
import time
import uuid
from enum import StrEnum

import aiosqlite
from loguru import logger

from datalake.config import Settings
from datalake.inference.accounting import (
    HUMAN_LABELER_PRICING_PER_DOC_USD,
    BudgetExceededError,
    estimate_gpt4_cost,
)
from datalake.inference.base import CallResult, InferenceClient
from datalake.loop.passes.critique import critique
from datalake.loop.passes.enrich import enrich
from datalake.loop.passes.propose import propose
from datalake.loop.passes.refine import refine
from datalake.loop.passes.vote import degrade_to_highest_confidence, vote
from datalake.prompts.templates import (
    Critique,
    EnrichedPayload,
    ProposalRecord,
    RefinedRecord,
    VoteResult,
)
from datalake.storage.db import (
    insert_catalog_record,
    insert_label_payload,
    insert_trace_event,
    update_dashboard_counters_on_doc_done,
    update_document_status,
)
from datalake.storage.models import CatalogRecord, Document, LabelPayload, TraceEvent


class State(StrEnum):
    INIT = "INIT"
    READ = "READ"
    PROPOSE_FANOUT = "PROPOSE_FANOUT"
    CRITIQUE_FANOUT = "CRITIQUE_FANOUT"
    REFINE = "REFINE"
    VOTE = "VOTE"
    ENRICH = "ENRICH"
    DONE = "DONE"
    FAILED = "FAILED"


# States from which we've produced enough to emit a partial (catalog-only) record.
_PARTIAL_OK_STATES = {State.VOTE, State.ENRICH}


class DocResult:
    """Carries through whatever each pass produced. Filled in incrementally."""

    def __init__(self, doc: Document) -> None:
        self.doc = doc
        self.proposals: list[ProposalRecord] = []
        self.critiques: list[Critique] = []
        self.refined: list[RefinedRecord] = []
        self.vote: VoteResult | None = None
        self.enriched: EnrichedPayload | None = None
        self.state: State = State.INIT
        self.partial: bool = False
        self.timeout: bool = False
        self.vote_degraded: bool = False
        # Per-doc cost accumulators (rolled up into dashboard_counters on completion).
        self.wafer_micro_usd: int = 0
        self.gpt4_micro_usd: int = 0  # estimated foil for this doc


class _PassGroupFailed(RuntimeError):
    """Internal: a whole pass group failed beyond recovery (e.g., <2 proposers succeed)."""


async def run_doc(
    doc: Document,
    doc_index: int,
    client: InferenceClient,
    heuristics_yaml: str,
    settings: Settings,
    per_doc_sem: asyncio.Semaphore,
    *,
    conn: aiosqlite.Connection,
    run_id: str,
) -> DocResult:
    """Run one doc through the 6-pass loop with a per-doc wall-clock budget.

    Partial-failure policy and trace events match docs/02-agent-loop.md.
    BudgetExceededError propagates upward — caller decides what to do with the run.
    """
    result = DocResult(doc)
    ceiling = settings.wafer_spend_ceiling_usd
    n = settings.n_proposers
    kw = {"conn": conn, "run_id": run_id, "ceiling_usd": ceiling}

    async with per_doc_sem:
        await update_document_status(conn, doc.id, "RUNNING")
        await conn.commit()

        try:
            async with asyncio.timeout(settings.per_doc_budget_seconds):
                result.state = State.READ
                if not doc.text:
                    raise _PassGroupFailed("READ: empty or missing document text")

                # --- PROPOSE × N (parallel) ---
                result.state = State.PROPOSE_FANOUT
                tasks = [
                    propose(doc, i, client, heuristics_yaml, **kw) for i in range(n)
                ]
                outcomes = await asyncio.gather(*tasks, return_exceptions=True)
                survivors: list[tuple[int, ProposalRecord]] = []
                for i, outcome in enumerate(outcomes):
                    if isinstance(outcome, BudgetExceededError):
                        raise outcome
                    if isinstance(outcome, BaseException):
                        await _trace_failure(conn, doc.id, run_id, "PROPOSE", i, outcome)
                    else:
                        cr, prop = outcome
                        survivors.append((i, prop))
                        result.proposals.append(prop)
                        _accumulate_cost(cr, result)
                        await _trace_ok(conn, doc.id, run_id, "PROPOSE", i, cr)
                await conn.commit()
                if len(survivors) < 2:
                    raise _PassGroupFailed(f"PROPOSE: only {len(survivors)} of {n} succeeded")

                # --- CRITIQUE × len(survivors) (parallel) ---
                result.state = State.CRITIQUE_FANOUT
                tasks = [
                    critique(doc, prop, idx, len(survivors), client, heuristics_yaml, **kw)
                    for idx, prop in survivors
                ]
                outcomes = await asyncio.gather(*tasks, return_exceptions=True)
                refine_pool: list[tuple[int, ProposalRecord, Critique | None]] = []
                for (idx, prop), outcome in zip(survivors, outcomes, strict=True):
                    if isinstance(outcome, BudgetExceededError):
                        raise outcome
                    if isinstance(outcome, BaseException):
                        await _trace_failure(conn, doc.id, run_id, "CRITIQUE", idx, outcome)
                        # Drop this proposal from the refine pool (skip refine for it).
                    else:
                        cr, crit = outcome
                        refine_pool.append((idx, prop, crit))
                        result.critiques.append(crit)
                        _accumulate_cost(cr, result)
                        await _trace_ok(conn, doc.id, run_id, "CRITIQUE", idx, cr)
                await conn.commit()
                if not refine_pool:
                    # All critiques failed — degraded path: refine raw proposals (no critic input).
                    refine_pool = [(idx, prop, None) for idx, prop in survivors]

                # --- REFINE × len(refine_pool) (parallel, but skip refine if critique was missing) ---
                result.state = State.REFINE
                tasks = [
                    refine(doc, prop, crit, client, heuristics_yaml, **kw) if crit is not None
                    else _passthrough_refine(prop)
                    for _, prop, crit in refine_pool
                ]
                outcomes = await asyncio.gather(*tasks, return_exceptions=True)
                for (idx, _, _), outcome in zip(refine_pool, outcomes, strict=True):
                    if isinstance(outcome, BudgetExceededError):
                        raise outcome
                    if isinstance(outcome, BaseException):
                        await _trace_failure(conn, doc.id, run_id, "REFINE", idx, outcome)
                    else:
                        cr, refined_rec = outcome
                        result.refined.append(refined_rec)
                        if cr is not None:
                            _accumulate_cost(cr, result)
                            await _trace_ok(conn, doc.id, run_id, "REFINE", idx, cr)
                await conn.commit()
                if not result.refined:
                    raise _PassGroupFailed("REFINE: no refined records produced")

                # --- VOTE — retry once, then degrade ---
                result.state = State.VOTE
                vote_result: VoteResult | None = None
                for attempt in range(2):
                    try:
                        cr, vote_result = await vote(
                            doc, result.refined, client, heuristics_yaml, **kw
                        )
                        _accumulate_cost(cr, result)
                        await _trace_ok(conn, doc.id, run_id, "VOTE", None, cr)
                        break
                    except BudgetExceededError:
                        raise
                    except Exception as e:  # noqa: BLE001 — vote failure is recoverable
                        await _trace_failure(conn, doc.id, run_id, "VOTE", None, e)
                        if attempt == 1:
                            vote_result = degrade_to_highest_confidence(result.refined)
                            result.vote_degraded = True
                assert vote_result is not None
                result.vote = vote_result
                winning = result.refined[
                    min(vote_result.winner_idx, len(result.refined) - 1)
                ]
                await conn.commit()

                # --- ENRICH — failure → partial, catalog-only emit ---
                result.state = State.ENRICH
                try:
                    cr, enriched = await enrich(doc, winning, client, heuristics_yaml, **kw)
                    result.enriched = enriched
                    _accumulate_cost(cr, result)
                    await _trace_ok(conn, doc.id, run_id, "ENRICH", None, cr)
                except BudgetExceededError:
                    raise
                except Exception as e:  # noqa: BLE001 — enrich failure is recoverable
                    await _trace_failure(conn, doc.id, run_id, "ENRICH", None, e)
                    result.partial = True

                # --- Persist catalog + label rows ---
                await _persist_outputs(conn, doc.id, winning, result.enriched, result.partial)
                result.state = State.DONE
                await update_document_status(conn, doc.id, "DONE", partial=result.partial)
                await _bump_counters(
                    conn, run_id, doc, result, vote_result.winner_confidence, failed=False
                )
                await conn.commit()

        except TimeoutError:
            result.timeout = True
            partial = result.state in _PARTIAL_OK_STATES
            result.state = State.FAILED if not partial else State.DONE
            await update_document_status(
                conn, doc.id, "DONE" if partial else "FAILED", partial=partial, timeout_flag=True
            )
            await _bump_counters(conn, run_id, doc, result, 0.0, failed=not partial)
            await conn.commit()
            logger.warning(f"doc {doc.id}: timeout in state {result.state} (partial={partial})")
        except _PassGroupFailed as e:
            result.state = State.FAILED
            await update_document_status(conn, doc.id, "FAILED")
            await _bump_counters(conn, run_id, doc, result, 0.0, failed=True)
            await conn.commit()
            logger.warning(f"doc {doc.id}: {e}")
        except BudgetExceededError:
            # Don't mark FAILED — leave as RUNNING; caller halts the whole run.
            raise

    return result


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


async def _passthrough_refine(prop: ProposalRecord) -> tuple[None, RefinedRecord]:
    """When critique failed, build a RefinedRecord directly from the raw proposal."""
    return None, RefinedRecord(
        **prop.model_dump(), revision_summary="No critique; raw proposal used as refined."
    )


def _accumulate_cost(cr: CallResult, result: DocResult) -> None:
    """Roll a call's cost into the doc's per-doc totals (wafer actual + gpt4 estimated foil)."""
    if cr.provider == "wafer":
        result.wafer_micro_usd += cr.cost_micro_usd
        result.gpt4_micro_usd += estimate_gpt4_cost(cr.tokens_in, cr.tokens_out)


async def _trace_ok(
    conn: aiosqlite.Connection,
    doc_id: str,
    run_id: str,
    pass_name: str,
    proposal_idx: int | None,
    cr: CallResult,
) -> None:
    now = time.time()
    await insert_trace_event(
        conn,
        TraceEvent(
            id=str(uuid.uuid4()),
            doc_id=doc_id,
            run_id=run_id,
            **{"pass": pass_name},
            proposal_idx=proposal_idx,
            started_at=now - (cr.latency_ms / 1000.0),
            ended_at=now,
            status="OK",
            tokens_in=cr.tokens_in,
            tokens_out=cr.tokens_out,
            cost_micro_usd=cr.cost_micro_usd,
        ),
    )


async def _trace_failure(
    conn: aiosqlite.Connection,
    doc_id: str,
    run_id: str,
    pass_name: str,
    proposal_idx: int | None,
    exc: BaseException,
) -> None:
    now = time.time()
    await insert_trace_event(
        conn,
        TraceEvent(
            id=str(uuid.uuid4()),
            doc_id=doc_id,
            run_id=run_id,
            **{"pass": pass_name},
            proposal_idx=proposal_idx,
            started_at=now,
            ended_at=now,
            status="FAILED",
            prompt_ref={"error": str(exc)[:300]},
        ),
    )


async def _persist_outputs(
    conn: aiosqlite.Connection,
    doc_id: str,
    winning: RefinedRecord,
    enriched: EnrichedPayload | None,
    partial: bool,
) -> None:
    """Materialise the per-doc catalog_record + label_payload."""
    catalog = CatalogRecord(
        doc_id=doc_id,
        content_type=winning.catalog.content_type.value,
        content_type_confidence=winning.catalog.content_type_confidence,
        ownership=winning.catalog.ownership.value,
        ownership_confidence=winning.catalog.ownership_confidence,
        ownership_rationale=winning.catalog.ownership_rationale,
        compliance_flags=[f.value for f in winning.catalog.compliance_flags],
        commercial_score=winning.catalog.commercial_score,
        commercial_action=winning.catalog.commercial_action.value,
    )
    await insert_catalog_record(conn, catalog)

    label = LabelPayload(
        doc_id=doc_id,
        structured_abstract=winning.label.structured_abstract,
        methodology={
            "named": winning.label.methodology_named,
            "other_freetext": winning.label.methodology_other_freetext,
        },
        novelty_claim=winning.label.novelty_claim,
        evidence_quality={
            "type": winning.label.evidence_type,
            "strength": winning.label.evidence_strength,
            "sample_size": winning.label.sample_size,
        },
        claim_graph=winning.label.claim_graph,
        citations=winning.label.citations,
        domain_tags=winning.label.domain_tags,
        enriched_payload=enriched.model_dump() if enriched else None,
        partial=partial,
    )
    await insert_label_payload(conn, label)


async def _bump_counters(
    conn: aiosqlite.Connection,
    run_id: str,
    doc: Document,
    result: DocResult,
    confidence: float,
    failed: bool,
) -> None:
    """Roll up this doc's costs + status into the dashboard counters."""
    human_usd = HUMAN_LABELER_PRICING_PER_DOC_USD.get(
        doc.content_type_guess or "other", HUMAN_LABELER_PRICING_PER_DOC_USD["other"]
    )
    await update_dashboard_counters_on_doc_done(
        conn,
        run_id,
        doc_wafer_micro_usd=result.wafer_micro_usd,
        doc_gpt4_micro_usd=result.gpt4_micro_usd,
        doc_human_labeler_micro_usd=int(human_usd * 1_000_000),
        doc_confidence=confidence,
        partial=result.partial,
        failed=failed,
    )


def should_verbose_trace(doc_index: int, sample_k: int) -> bool:
    """True for every K-th doc (K=10 default). See docs/02 §Visualizer sampling."""
    return doc_index % sample_k == 0
