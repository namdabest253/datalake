# 06. Dashboard

Streamlit single-page app with 6 panels. Reads from SQLite (WAL mode). Polls — no websockets, no SSE.

## Page layout

```
┌──────────────────────────────────────────────────────────────────────────┐
│  LakeAudit — Run: 2026-05-16-1735       (N=3, K=10, ceiling=$30)         │
│  "Scale AI labels data. LakeAudit makes university data labelable."      │
├──────────────────────────────────────────────────────────────────────────┤
│ ┌───────────────────────────┐ ┌──────────────────────────────────────┐   │
│ │  1. DOCUMENT STREAM       │ │  2. AGENT LOOP VISUALIZER            │   │
│ │  docs/sec: 12.4           │ │  (sampled doc: arxiv/2024.12345.pdf) │   │
│ │  total: 8,742             │ │                                      │   │
│ │  [latest 20 records ...]  │ │  READ ── PROPOSE×3 ── CRITIQUE×3 ──  │   │
│ │                           │ │  REFINE×3 ── VOTE ── ENRICH ── DONE  │   │
│ │                           │ │  [animated bubbles, 250ms refresh]   │   │
│ └───────────────────────────┘ └──────────────────────────────────────┘   │
│ ┌───────────────────────────┐ ┌──────────────────────────────────────┐   │
│ │  3. QUALITY METRICS       │ │  4. COST METER                       │   │
│ │  avg confidence: 0.81     │ │  Wafer:           $4.21    (actual)  │   │
│ │  low-conf flag %: 7.2%    │ │  GPT-4 foil:    $1,847     (est.)    │   │
│ │  inter-agent agreement:   │ │  Human labeler: $437,100   (est.)    │   │
│ │    0.74                   │ │  vs GPT-4:    438× cheaper           │   │
│ │                           │ │  vs human:  103,800× cheaper         │   │
│ │                           │ │  ⓘ Foils estimated, no real spend.   │   │
│ │                           │ │    GPT-4: tokens × public pricing.   │   │
│ │                           │ │    Human: $50/paper (Surge/Scale     │   │
│ │                           │ │    midpoint, PRD §3). GPT-4 runs     │   │
│ │                           │ │    only on the 200-doc eval subset;  │   │
│ │                           │ │    no human labels are produced.     │   │
│ └───────────────────────────┘ └──────────────────────────────────────┘   │
│ ┌───────────────────────────┐ ┌──────────────────────────────────────┐   │
│ │  5. CATALOG FILTER VIEW   │ │  6. SIDE-BY-SIDE EVAL                │   │
│ │  (post-run only)          │ │  win rate: 71% vs GPT-4              │   │
│ │  [☒] license_ready        │ │  per-dimension deltas:               │   │
│ │  [ ] needs_consent        │ │    methodology: +0.8                 │   │
│ │  score ≥ [70]             │ │    novelty:    +0.6                  │   │
│ │  → 3,142 docs             │ │    evidence:   +0.4                  │   │
│ │  est value: $2.3M         │ │    ... (full table)                  │   │
│ └───────────────────────────┘ └──────────────────────────────────────┘   │
└──────────────────────────────────────────────────────────────────────────┘
```

## Refresh mechanism

- **`st_autorefresh` at 1Hz** for panels 1, 3, 4 (counters and streams).
- **250ms refresh** for panel 2 (visualizer) — picks a verbose-traced doc and animates its trace events.
- **No refresh** for panels 5 (post-run filter) and 6 (eval results, populated by `lakeaudit eval`).

All reads come from SQLite. WAL mode allows concurrent reads with the writer. No websockets, no SSE.

Justification: the loop writer process is on the same machine; latency is sub-millisecond; bounded data sizes (latest N rows for streams, pre-aggregated counters for everything else) keep query time well under the refresh interval.

## Per-panel data source (`lakeaudit/dashboard/queries.py`)

### Panel 1: Document stream

Refresh: 1Hz.

```sql
-- latest 20 finalized records
SELECT d.id, d.source_path, c.content_type, c.commercial_action,
       c.commercial_score, c.compliance_flags
FROM documents d
JOIN catalog_records c ON c.doc_id = d.id
WHERE d.run_id = :run_id AND d.status = 'DONE'
ORDER BY d.ingested_at DESC
LIMIT 20;

-- docs/sec from materialized counter
SELECT docs_done, updated_at FROM dashboard_counters WHERE run_id = :run_id;
```

`docs/sec` computed in Python from delta since previous poll.

### Panel 2: Agent loop visualizer

Refresh: 250ms.

```sql
-- pick a recent verbose-traced doc
SELECT id FROM documents
WHERE run_id = :run_id AND status IN ('RUNNING', 'DONE')
  AND id IN (SELECT DISTINCT doc_id FROM trace_events WHERE prompt_ref IS NOT NULL)
ORDER BY ingested_at DESC LIMIT 1;

-- fetch all trace events for that doc
SELECT id, pass, proposal_idx, parent_event_id, status, started_at, ended_at,
       prompt_ref, response_ref, tokens_in, tokens_out
FROM trace_events
WHERE doc_id = :doc_id
ORDER BY started_at;
```

Rendered as a tree using `streamlit-elements` or Graphviz. Hover shows prompt/response.

### Panel 3: Quality metrics

Refresh: 1Hz.

```sql
SELECT avg_overall_confidence, docs_done, docs_partial, docs_failed
FROM dashboard_counters WHERE run_id = :run_id;

-- low-conf flag rate (small windowed query)
SELECT
  SUM(CASE WHEN ownership_confidence < 0.5 THEN 1 ELSE 0 END) * 1.0 / COUNT(*) AS low_conf_pct
FROM catalog_records c JOIN documents d ON d.id = c.doc_id
WHERE d.run_id = :run_id;
```

Inter-agent agreement: computed from the trace as fraction of docs where ≥2 of 3 proposers agreed on `content_type` and `ownership`.

### Panel 4: Cost meter

Refresh: 1Hz.

```sql
SELECT total_wafer_micro_usd,
       total_gpt4_equivalent_micro_usd,
       total_human_labeler_equivalent_micro_usd
FROM dashboard_counters WHERE run_id = :run_id;
```

Render all three numbers, abbreviating large ones (`$1.8K`, `$437K`, `$1.2M`). Show two ratios: `vs GPT-4 = gpt4 / wafer`, `vs human = human / wafer`, each rounded to the nearest integer. Sources: Wafer row is per-call actuals from `inference_calls`; GPT-4 row is per-call estimated rows (foil mechanism in [`05`](05-inference-client.md)); human-labeler row is a per-doc counter (also detailed in [`05`](05-inference-client.md)).

**Always display the foil methodology annotation** below the numbers (small italic gray text — see ASCII wireframe above). This is non-negotiable and not user-dismissable.

The three-foil comparison is the core competitive claim from PRD §3 ("Scale AI labels data. LakeAudit makes university data labelable in the first place."). Wafer beats GPT-4 by ~500× and beats Surge-tier human labeling by ~30,000–100,000× depending on corpus size — the latter ratio is the one that decides whether the institutional-seller market exists at all.

### Panel 5: Catalog filter view (post-run only)

Refresh: on user action.

```sql
SELECT d.id, d.source_path, c.content_type, c.commercial_action,
       c.commercial_score, c.compliance_flags
FROM documents d
JOIN catalog_records c ON c.doc_id = d.id
WHERE d.run_id = :run_id
  AND c.commercial_action IN (:selected_actions)
  AND c.commercial_score >= :min_score
ORDER BY c.commercial_score DESC;
```

Estimated total market value: sum over license-ready docs of a per-content-type dollar table (constants in `lakeaudit/dashboard/panels/filter.py`):

```python
# Per-doc estimated lifetime commercial value to AI labs as labeled training data.
# Basis: PRD §3 establishes ~$1–$10 per high-quality scientific datapoint as the
# buyer-side price. A research paper typically yields tens to low hundreds of
# datapoints (sections, claims, QA pairs), putting per-paper values in the
# $100–$1,500 range. Numbers below are demo-grade midpoints; tune against real
# buyer conversations before claiming a hard market value to the institution.
ESTIMATED_VALUE_PER_DOC = {
    "research_paper":      800,
    "grant_proposal":      200,
    "dataset_description": 1500,
    "faculty_publication": 600,
    "other":               100,
}
```

### Panel 6: Side-by-side eval

Refresh: on `lakeaudit eval` completion (manual refresh button or auto on dashboard reload).

Pseudo-SQL (the actual unblinding done in Python after fetch):

```sql
SELECT p.id, p.a_is_lakeaudit, r.winner, r.dimension_scores
FROM eval_pairs p
JOIN eval_results r ON r.pair_id = p.id
WHERE p.run_id = :run_id;
```

Python aggregator computes:

```python
winners = [resolve_winner(row.a_is_lakeaudit, row.winner) for row in rows]
win_rate = winners.count("lakeaudit") / sum(1 for w in winners if w != "tie")
dim_deltas = {dim: mean(lakeaudit_score[dim] - gpt4_score[dim] for row in rows)
              for dim in DIMENSIONS}
```

## Materialized counters

`dashboard_counters` is updated by the loop's per-doc completion handler (single writer per doc) — not by triggers. Pseudocode:

```python
async def on_doc_done(doc_id, run_id, doc_wafer_cost, doc_gpt4_cost, doc_confidence):
    async with db.write() as conn:
        await conn.execute("""
          UPDATE dashboard_counters
          SET docs_done = docs_done + 1,
              total_wafer_micro_usd = total_wafer_micro_usd + ?,
              total_gpt4_equivalent_micro_usd = total_gpt4_equivalent_micro_usd + ?,
              avg_overall_confidence = ((avg_overall_confidence * docs_done) + ?) / (docs_done + 1),
              updated_at = ?
          WHERE run_id = ?
        """, (doc_wafer_cost, doc_gpt4_cost, doc_confidence, time.time(), run_id))
```

Dashboard reads this row in O(1) per panel poll instead of running aggregate queries over `inference_calls` or `trace_events`.

## Performance budget

- 6 panels × 1Hz × O(1) counter reads = 6 queries/sec from the dashboard.
- Plus visualizer at 4Hz on one doc's trace = 4 queries/sec.
- Plus panel 1's "latest 20" query at 1Hz = 1 query/sec.
- Total: ~11 queries/sec, all bounded-size, all WAL-compatible.

This is comfortably below SQLite's read throughput. If query latency creeps above 200ms, the K=10 trace sampling is the first knob to reduce.

## Failure modes

- **Loop process dies mid-run** → dashboard keeps reading the last-committed state. Counter freezes. Restart loop with `lakeaudit run --continue`.
- **Dashboard process dies** → loop unaffected. Restart `streamlit run`.
- **SQLite corruption** (rare) → no recovery in MVP; re-run from scratch. Mitigation: `--persist` flag is opt-in.
