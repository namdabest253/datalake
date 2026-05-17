# 02. Agent loop

The 6-pass loop is the product. This file specifies state machine, per-pass contracts, fan-out math, failure handling, and trace contract. Prompt content and JSON schemas live in [`03`](03-prompts-and-schemas.md).

## State machine

```
READ ──▶ PROPOSE_FANOUT ──▶ CRITIQUE_FANOUT ──▶ REFINE ──▶ VOTE ──▶ ENRICH ──▶ DONE
  │             │                  │              │         │         │
  │             │                  │              │         │         └──▶ DONE (catalog-only, partial=true)
  │             │                  │              │         │
  │             │                  │              │         └────────────▶ ENRICH (retry vote once; degrade)
  │             │                  │              │
  │             │                  │              └──────────────────────▶ FAILED (if all refines fail)
  │             │                  │
  │             │                  └─────────────────────────────────────▶ REFINE (drop critique-failed proposals)
  │             │
  │             └─────────────────────────────────────────────────────────▶ FAILED (if <2 proposers succeed)
  │
  └─────────────────────────────────────────────────────────────────────▶ FAILED (parse error)
```

| From | To | Trigger |
|---|---|---|
| INIT | READ | Doc dequeued by loop runner |
| READ | PROPOSE_FANOUT | Text extracted, passes pydantic `Document` validation |
| READ | FAILED | PyMuPDF parse error or empty text |
| PROPOSE_FANOUT | CRITIQUE_FANOUT | ≥2 of 3 proposers returned valid `ProposalRecord` |
| PROPOSE_FANOUT | FAILED | <2 proposers succeeded |
| CRITIQUE_FANOUT | REFINE | All non-failed critiques complete (failed critiques drop their proposal from refine) |
| REFINE | VOTE | ≥1 refined record exists |
| REFINE | FAILED | All refines failed |
| VOTE | ENRICH | Vote returned a `VoteResult` (after up to 1 retry) |
| VOTE | ENRICH (degraded) | Vote failed twice → pick highest-confidence refined record |
| ENRICH | DONE | `EnrichedPayload` returned |
| ENRICH | DONE (partial) | Enrich failed → catalog-only emit, `label_payload.enriched_payload=null`, `partial=true` |
| any | FAILED | 30s wall-clock budget exceeded |

## Per-pass contract

| Pass | Calls/doc | Input | Output (schema → [`03`](03-prompts-and-schemas.md)) | Latency band | On failure |
|---|---|---|---|---|---|
| READ | 0 | File path | `Document(text, references, metadata)` | <500ms | FAILED |
| PROPOSE | 3 parallel | `Document` | `ProposalRecord` (catalog + label fields, all confidences) | <2s | Drop proposal; FAILED if <2 succeed |
| CRITIQUE | 3 parallel (1 per proposal) | `ProposalRecord` + heuristics | `Critique` (per-field flags + suggestions) | <2s | Skip proposal in refine |
| REFINE | up to 3 parallel | `(ProposalRecord, Critique)` | `RefinedRecord` (revised proposal + `revision_summary`) | <2s | Drop refine; FAILED if none succeed |
| VOTE | 1 | All `RefinedRecord`s | `VoteResult(winner_idx, confidence, rationale)` | <1s | Retry once; then degrade to highest-confidence refined |
| ENRICH | 1 | Winning `RefinedRecord` + `Document` | `EnrichedPayload` | <2s | Catalog-only emit, `partial=true` |

**Total baseline calls per doc**: 3 + 3 + 3 + 1 + 1 = **11**. Within PRD §7's "10–20 calls per document" envelope.

**Total expected wall-clock per doc**: <5s end-to-end (PRD §9). **Per-doc hard budget: 30s** (covers slow Wafer responses; cancels remaining tasks via task group on exceed).

## Fan-out shape

**Critique pass: one critique call per proposal** (not one critic-sees-all). Rationale:

- More parallel — 3 critique calls in flight, no serial dependency.
- More dramatic for the visualizer — 3 critique bubbles parallel to 3 proposal bubbles.
- Cheaper per call (each critique sees one proposal, smaller context).

**Refine pass: one refine call per surviving proposal** (1:1 with critiques). Preserves the N parallel tracks until vote.

**Vote pass: one call that sees all surviving refined records.** Single consensus call is the canonical voter pattern; no fan-out needed.

**Enrich pass: one call** on the winning refined record + original document text. Produces the AI-lab-ready payload.

## Partial-failure policy

| Failure | Policy |
|---|---|
| 1 of 3 proposers fails (parse, schema, or 5xx after retries) | Continue with 2 survivors |
| ≥2 of 3 proposers fail | Doc → FAILED, no catalog or label record |
| 1 critique fails | Drop the associated proposal from refine pool |
| All critiques fail | Skip critique step, refine the raw proposals (rare; degraded quality but not blocking) |
| 1 refine fails | Drop that refined record from vote pool |
| All refines fail | Doc → FAILED |
| Vote fails on first try | Retry once with `temperature=0` |
| Vote fails twice | Degrade: pick refined record with highest `overall_confidence`; mark `vote_degraded=true` in trace |
| Enrich fails | Emit catalog-only record (`label_payload.enriched_payload=null`), set `partial=true` |
| 30s wall-clock exceeded | Cancel all in-flight tasks, emit whatever completed, mark `timeout=true` |

`partial=true` and `timeout=true` propagate to the export and are visible in the dashboard's low-confidence filter.

## Cancellation & budget

Implemented via `asyncio.timeout()` wrapped around the per-doc task group:

```python
async with asyncio.timeout(30):
    async with asyncio.TaskGroup() as tg:
        # propose, critique, refine, vote, enrich orchestration
        ...
```

On timeout, the task group cancels all in-flight tasks. The orchestrator catches `TimeoutError`, gathers completed pass outputs, writes whatever it has to storage with `timeout=true`.

Per-call timeouts (20s) are a separate budget enforced in [`05-inference-client.md`](05-inference-client.md); doc-level budget is the hard outer bound.

## Determinism knobs

| Pass | Temperature | Why |
|---|---|---|
| PROPOSE | 0.8 | Want diverse independent drafts |
| CRITIQUE | 0.4 | Some variation OK but should be opinionated |
| REFINE | 0.2 | Mostly mechanical merge of critique into proposal |
| VOTE | 0.0 | Deterministic selection |
| ENRICH | 0.5 | Some creativity in summarization, anchored to source |

Seed where provider supports it. Pass-specific `top_p` and `frequency_penalty` defaults in `lakeaudit/prompts/templates.py`.

## Trace contract

Every state transition writes a `trace_events` row (schema in [`04-data-model.md`](04-data-model.md)):

- `id` — UUID
- `doc_id`, `run_id`
- `pass` — enum: `READ | PROPOSE | CRITIQUE | REFINE | VOTE | ENRICH`
- `proposal_idx` — `0..N-1` for fan-out passes, `NULL` otherwise
- `parent_event_id` — links sequential passes (READ → PROPOSE → CRITIQUE etc.) and fan-out tracks (each PROPOSE#i → its CRITIQUE#i → its REFINE#i share a chain)
- `started_at`, `ended_at`, `status` (`OK | FAILED | TIMEOUT`)
- `prompt_ref`, `response_ref` — inline JSON for verbose-traced docs, NULL otherwise
- `tokens_in`, `tokens_out`, `cost_micro_usd`

The trace graph for one doc is a tree:

```
READ ─┬─ PROPOSE#1 ── CRITIQUE#1 ── REFINE#1 ─┐
      ├─ PROPOSE#2 ── CRITIQUE#2 ── REFINE#2 ─┼── VOTE ── ENRICH
      └─ PROPOSE#3 ── CRITIQUE#3 ── REFINE#3 ─┘
```

The dashboard visualizer panel ([`06`](06-dashboard.md)) renders this tree for sampled docs.

## Visualizer sampling

**K=10.** Every 10th doc (`doc_index % 10 == 0`) is **verbose-traced**: prompts and responses captured inline in `trace_events`. Other docs record only metadata (timings, token counts, status).

Rationale:

- Keeps `trace_events` table size manageable for 20k-doc demo runs.
- Dashboard visualizer always has fresh material rotating in.
- Disk + WAL contention stay bounded.

Override via `--debug` flag (forces verbose on all docs) or `--sample-rate=N` (overrides K).
