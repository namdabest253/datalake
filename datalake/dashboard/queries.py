"""Verbatim SQL used by the 6 dashboard panels.

See docs/06-dashboard.md §Per-panel data source.
"""

from __future__ import annotations

# Panel 1: Document stream
LATEST_RECORDS = """
SELECT d.id, d.source_path, c.content_type, c.commercial_action,
       c.commercial_score, c.compliance_flags
FROM documents d
JOIN catalog_records c ON c.doc_id = d.id
WHERE d.run_id = :run_id AND d.status = 'DONE'
ORDER BY d.ingested_at DESC
LIMIT 20
"""

DOCS_PER_SEC_COUNTER = """
SELECT docs_done, updated_at FROM dashboard_counters WHERE run_id = :run_id
"""

# Panel 2: Agent loop visualizer
PICK_VERBOSE_TRACED_DOC = """
SELECT id FROM documents
WHERE run_id = :run_id AND status IN ('RUNNING', 'DONE')
  AND id IN (SELECT DISTINCT doc_id FROM trace_events WHERE prompt_ref IS NOT NULL)
ORDER BY ingested_at DESC LIMIT 1
"""

TRACE_FOR_DOC = """
SELECT id, pass, proposal_idx, parent_event_id, status, started_at, ended_at,
       prompt_ref, response_ref, tokens_in, tokens_out
FROM trace_events
WHERE doc_id = :doc_id
ORDER BY started_at
"""

# Panel 3: Quality metrics
QUALITY_COUNTERS = """
SELECT avg_overall_confidence, docs_done, docs_partial, docs_failed
FROM dashboard_counters WHERE run_id = :run_id
"""

LOW_CONF_FLAG_RATE = """
SELECT SUM(CASE WHEN ownership_confidence < 0.5 THEN 1 ELSE 0 END) * 1.0 / COUNT(*) AS low_conf_pct
FROM catalog_records c JOIN documents d ON d.id = c.doc_id
WHERE d.run_id = :run_id
"""

# Panel 4: Cost meter (3-row foil — Wafer, GPT-4, human labeler)
COST_METER = """
SELECT total_wafer_micro_usd,
       total_gpt4_equivalent_micro_usd,
       total_human_labeler_equivalent_micro_usd
FROM dashboard_counters WHERE run_id = :run_id
"""

# Panel 5: Catalog filter view (post-run only)
FILTERED_CATALOG = """
SELECT d.id, d.source_path, c.content_type, c.commercial_action,
       c.commercial_score, c.compliance_flags
FROM documents d
JOIN catalog_records c ON c.doc_id = d.id
WHERE d.run_id = :run_id
  AND c.commercial_action IN (:selected_actions)
  AND c.commercial_score >= :min_score
ORDER BY c.commercial_score DESC
"""

# Panel 6: Side-by-side eval (Python unblinds after fetch)
EVAL_RESULTS = """
SELECT p.id, p.a_is_datalake, r.winner, r.dimension_scores
FROM eval_pairs p
JOIN eval_results r ON r.pair_id = p.id
WHERE p.run_id = :run_id
"""
