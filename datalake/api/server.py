"""Read-only aiohttp API that mirrors the shapes used by the React frontend.

Endpoints intentionally return the exact shape `frontend/src/data/mock.ts` declares
so that swapping the data source in each page is a one-line change rather than a
re-typing exercise. See `frontend/src/api/client.ts` for the typed call sites.

Run via `datalake api --port 8000`. The vite dev server runs on 5173 and hits this
process across origins, so CORS is open by default for any localhost origin.
"""

from __future__ import annotations

import json
import sqlite3
from collections.abc import Callable
from pathlib import Path
from typing import Any

from aiohttp import web

from datalake.config import load_settings

# ---------------------------------------------------------------------------
# DB helpers — sync sqlite3 is fine for short read queries; aiohttp handlers
# run in the asyncio event loop but each query takes <1ms on this dataset.
# ---------------------------------------------------------------------------


def _db_path() -> Path:
    return load_settings().paths.sqlite_db


def _read(sql: str, params: tuple = ()) -> list[sqlite3.Row]:
    """Run a SELECT and return all rows. Empty list if DB or table missing."""
    path = _db_path()
    if not path.exists():
        return []
    try:
        conn = sqlite3.connect(str(path))
        conn.row_factory = sqlite3.Row
        try:
            return conn.execute(sql, params).fetchall()
        finally:
            conn.close()
    except sqlite3.OperationalError:
        return []


def _read_one(sql: str, params: tuple = ()) -> sqlite3.Row | None:
    rows = _read(sql, params)
    return rows[0] if rows else None


def _resolve_run_id(request: web.Request) -> str | None:
    """`?run_id=...` wins; else most-recent run that has at least one document.

    The fallback to a doc-bearing run keeps demos sane when intermediate test
    runs (e.g. eval scaffolds) have inserted rows in `runs` but no documents.
    """
    explicit = request.query.get("run_id")
    if explicit:
        return explicit
    row = _read_one(
        "SELECT r.id FROM runs r "
        "WHERE EXISTS (SELECT 1 FROM documents d WHERE d.run_id=r.id) "
        "ORDER BY r.started_at DESC LIMIT 1"
    )
    if row is not None:
        return row["id"]
    # No run has documents — return the newest run so endpoints don't blow up.
    row = _read_one("SELECT id FROM runs ORDER BY started_at DESC LIMIT 1")
    return row["id"] if row else None


def _json_safe(raw: Any, default: Any) -> Any:
    if raw is None:
        return default
    try:
        return json.loads(raw)
    except (json.JSONDecodeError, TypeError):
        return default


# ---------------------------------------------------------------------------
# Shape adapters — convert DB rows into the frontend mock-data shape.
# ---------------------------------------------------------------------------

# `documents.status` → frontend `StreamItem.status`. Maps the loop's lifecycle
# states to the visual states the UI already understands.
_DOC_STATUS_MAP = {
    "DONE": "Ready",
    "RUNNING": "Extracting",
    "FAILED": "Failed",
    "INGESTED": "Queued",
}

# Loose content-type → material-icons mapping. Friend's UI keys on these names.
_ICON_FOR_CONTENT_TYPE = {
    "research_paper": "description",
    "grant_proposal": "article",
    "dataset_description": "dataset",
    "faculty_publication": "school",
    "other": "folder",
    None: "folder",
}

# Compliance flag list → frontend `compliance` tri-state + label.
_RESTRICTED_FLAGS = {"ferpa", "hipaa", "irb_restricted", "publisher_exclusive"}
_CLEAN_FLAGS = {"clean", "public_domain"}


def _compliance_tristate(flags: list[str]) -> tuple[str, str]:
    """Return (compliance, complianceLabel) from a flag list."""
    flag_set = {f.lower() for f in flags}
    restricted = flag_set & _RESTRICTED_FLAGS
    if restricted:
        # Capitalise the dominant flag for the label.
        label = sorted(restricted)[0].upper()
        return "restricted", label
    if flag_set & _CLEAN_FLAGS:
        return "clean", "Clean"
    return "unclear", "Unclear"


# ---------------------------------------------------------------------------
# Handlers — one per endpoint, kept terse.
# ---------------------------------------------------------------------------


async def handle_health(_request: web.Request) -> web.Response:
    return web.json_response({"ok": True, "db": str(_db_path()), "db_exists": _db_path().exists()})


async def handle_runs(_request: web.Request) -> web.Response:
    """All runs, newest first. Frontend uses these to populate a run picker if it wants."""
    rows = _read(
        "SELECT id, started_at, ended_at, corpus_version FROM runs ORDER BY started_at DESC"
    )
    return web.json_response(
        [
            {
                "id": r["id"],
                "started_at": r["started_at"],
                "ended_at": r["ended_at"],
                "corpus_version": r["corpus_version"],
            }
            for r in rows
        ]
    )


async def handle_stream(request: web.Request) -> web.Response:
    """`StreamItem[]` — latest docs for the active run with status mapped to UI labels."""
    run_id = _resolve_run_id(request)
    if run_id is None:
        return web.json_response([])
    limit = int(request.query.get("limit", "20"))
    rows = _read(
        "SELECT d.id, d.source_path, d.status, d.content_type_guess, "
        "       c.content_type FROM documents d "
        "LEFT JOIN catalog_records c ON c.doc_id = d.id "
        "WHERE d.run_id=? ORDER BY d.ingested_at DESC LIMIT ?",
        (run_id, limit),
    )
    out = []
    for r in rows:
        ctype = r["content_type"] or r["content_type_guess"] or "other"
        out.append(
            {
                "id": r["id"],
                "filename": Path(r["source_path"]).name,
                "contentType": _humanise_content_type(ctype),
                "status": _DOC_STATUS_MAP.get(r["status"], "Queued"),
                "iconName": _ICON_FOR_CONTENT_TYPE.get(ctype, "description"),
            }
        )
    return web.json_response(out)


async def handle_catalog(request: web.Request) -> web.Response:
    """`CatalogRow[]` — catalog records joined with ownership, scored, compliance-bucketed."""
    run_id = _resolve_run_id(request)
    if run_id is None:
        return web.json_response([])
    min_score = int(request.query.get("min_score", "0"))
    limit = int(request.query.get("limit", "200"))
    rows = _read(
        "SELECT d.id, d.source_path, c.content_type, c.commercial_score, "
        "       c.compliance_flags, c.ownership_rationale "
        "FROM documents d JOIN catalog_records c ON c.doc_id=d.id "
        "WHERE d.run_id=? AND c.commercial_score >= ? "
        "ORDER BY c.commercial_score DESC LIMIT ?",
        (run_id, min_score, limit),
    )
    out = []
    for r in rows:
        flags = _json_safe(r["compliance_flags"], [])
        compliance, label = _compliance_tristate(flags)
        out.append(
            {
                "id": r["id"],
                "name": _name_from_path(r["source_path"]),
                "owner": _shorten_owner(r["ownership_rationale"]),
                "compliance": compliance,
                "complianceLabel": label,
                "score": int(r["commercial_score"]),
                "iconName": _ICON_FOR_CONTENT_TYPE.get(r["content_type"], "description"),
            }
        )
    return web.json_response(out)


async def handle_recent_uploads(_request: web.Request) -> web.Response:
    """Mock shape `RECENT_UPLOADS` — most-recent runs framed as ingestion batches."""
    rows = _read(
        "SELECT r.id, r.corpus_version, r.started_at, r.ended_at, "
        "       (SELECT COUNT(*) FROM documents d WHERE d.run_id=r.id) AS doc_count, "
        "       (SELECT COUNT(*) FROM documents d WHERE d.run_id=r.id "
        "        AND d.status IN ('DONE','RUNNING','FAILED')) AS processed "
        "FROM runs r ORDER BY r.started_at DESC LIMIT 5"
    )
    out = []
    for r in rows:
        total = int(r["doc_count"])
        processed = int(r["processed"])
        progress = int(round(processed / total * 100)) if total else 0
        status = "Completed" if r["ended_at"] is not None or progress >= 100 else "Processing"
        out.append(
            {
                "id": r["id"],
                "name": _name_from_corpus(r["corpus_version"], r["id"]),
                "files": total,
                "status": status,
                "progress": progress,
                "iconName": "folder",
            }
        )
    return web.json_response(out)


async def handle_eval_dimensions(request: web.Request) -> web.Response:
    """`EVAL_DIMENSIONS` shape — per-dimension Datalake win rate vs GPT-4."""
    run_id = _resolve_run_id(request)
    if run_id is None:
        return web.json_response([])
    rows = _read(
        "SELECT p.a_is_datalake, r.dimension_scores "
        "FROM eval_results r JOIN eval_pairs p ON p.id=r.pair_id "
        "WHERE p.run_id=?",
        (run_id,),
    )
    if not rows:
        return web.json_response([])
    # Datalake "wins" a dimension when its score is strictly higher than GPT-4's on that pair.
    wins: dict[str, int] = {}
    decided: dict[str, int] = {}
    for r in rows:
        is_dl_a = bool(r["a_is_datalake"])
        scores = _json_safe(r["dimension_scores"], {})
        for dim, pair in (scores or {}).items():
            if not isinstance(pair, dict):
                continue
            try:
                a = float(pair.get("A", pair.get("a", 0)))
                b = float(pair.get("B", pair.get("b", 0)))
            except (TypeError, ValueError):
                continue
            if a == b:
                continue
            decided[dim] = decided.get(dim, 0) + 1
            if (a > b and is_dl_a) or (b > a and not is_dl_a):
                wins[dim] = wins.get(dim, 0) + 1
    out = [
        {
            "name": _humanise_dimension(dim),
            "winRate": round(wins.get(dim, 0) / decided[dim] * 100),
        }
        for dim in sorted(decided)
    ]
    return web.json_response(out)


async def handle_export_sample(request: web.Request) -> web.Response:
    """`SAMPLE_EXPORT_RECORD` — pretty-printed first row from the latest exported JSONL."""
    run_id = _resolve_run_id(request)
    if run_id is None:
        return web.json_response({"sample": "", "available": False})
    export_path = Path(".datalake/export") / f"{run_id}.jsonl"
    if not export_path.exists():
        return web.json_response(
            {
                "sample": "",
                "available": False,
                "hint": f"Run `datalake export --run-id {run_id}` to generate the JSONL.",
            }
        )
    with export_path.open("r", encoding="utf-8") as fh:
        first = fh.readline().strip()
    if not first:
        return web.json_response({"sample": "", "available": False})
    try:
        pretty = json.dumps(json.loads(first), indent=2, ensure_ascii=False)
    except json.JSONDecodeError:
        pretty = first
    return web.json_response({"sample": pretty, "available": True})


async def handle_counters(request: web.Request) -> web.Response:
    """Live counters for the Dashboard hero (docs done, costs, avg confidence)."""
    run_id = _resolve_run_id(request)
    if run_id is None:
        return web.json_response(_empty_counters())
    row = _read_one(
        "SELECT docs_done, docs_failed, docs_partial, "
        "       total_wafer_micro_usd, total_gpt4_equivalent_micro_usd, "
        "       total_human_labeler_equivalent_micro_usd, "
        "       avg_overall_confidence "
        "FROM dashboard_counters WHERE run_id=?",
        (run_id,),
    )
    if row is None:
        return web.json_response(_empty_counters() | {"run_id": run_id})
    wafer = int(row["total_wafer_micro_usd"])
    gpt4 = int(row["total_gpt4_equivalent_micro_usd"])
    human = int(row["total_human_labeler_equivalent_micro_usd"])
    return web.json_response(
        {
            "run_id": run_id,
            "docs_done": int(row["docs_done"]),
            "docs_failed": int(row["docs_failed"]),
            "docs_partial": int(row["docs_partial"]),
            "wafer_usd": wafer / 1_000_000,
            "gpt4_equivalent_usd": gpt4 / 1_000_000,
            "human_labeler_equivalent_usd": human / 1_000_000,
            "avg_overall_confidence": float(row["avg_overall_confidence"]),
            "cost_ratio_vs_gpt4": (gpt4 / wafer) if wafer else None,
            "cost_ratio_vs_human": (human / wafer) if wafer else None,
        }
    )


async def handle_active_trace(request: web.Request) -> web.Response:
    """Pick the most-active doc and return its trace tree for the Dashboard visualiser.

    "Most-active" = a RUNNING doc if any, else the most-recently-finished one. Returns
    one entry per pass (READ/PROPOSE/CRITIQUE/REFINE/VOTE/ENRICH) summarised across
    its proposal_idx fan-out, in the shape the Dashboard's LoopStep renders.
    """
    run_id = _resolve_run_id(request)
    if run_id is None:
        return web.json_response({"available": False})
    doc = _read_one(
        "SELECT id, source_path FROM documents WHERE run_id=? "
        "AND status IN ('RUNNING','DONE') "
        "ORDER BY CASE WHEN status='RUNNING' THEN 0 ELSE 1 END, ingested_at DESC LIMIT 1",
        (run_id,),
    )
    if doc is None:
        return web.json_response({"available": False})
    doc_id = doc["id"]
    events = _read(
        'SELECT "pass" AS pass_, status, proposal_idx, started_at, ended_at '
        "FROM trace_events WHERE doc_id=? ORDER BY started_at",
        (doc_id,),
    )
    # Group by pass, aggregate fan-out width.
    order = ["READ", "PROPOSE", "CRITIQUE", "REFINE", "VOTE", "ENRICH"]
    by_pass: dict[str, dict[str, Any]] = {}
    for ev in events:
        p = ev["pass_"]
        bucket = by_pass.setdefault(p, {"ok": 0, "failed": 0, "min_t": None, "max_t": None})
        if ev["status"] == "OK":
            bucket["ok"] += 1
        elif ev["status"] in ("FAILED", "TIMEOUT"):
            bucket["failed"] += 1
        if ev["started_at"] is not None:
            bucket["min_t"] = (
                ev["started_at"] if bucket["min_t"] is None else min(bucket["min_t"], ev["started_at"])
            )
        if ev["ended_at"] is not None:
            bucket["max_t"] = (
                ev["ended_at"] if bucket["max_t"] is None else max(bucket["max_t"], ev["ended_at"])
            )
    passes = []
    for p in order:
        bucket = by_pass.get(p)
        if bucket is None:
            passes.append({"pass": p, "state": "pending", "ok": 0, "failed": 0, "latency_ms": None})
            continue
        latency_ms = (
            int((bucket["max_t"] - bucket["min_t"]) * 1000)
            if bucket["min_t"] is not None and bucket["max_t"] is not None
            else None
        )
        state = "done" if bucket["ok"] and not bucket["failed"] else "failed" if bucket["failed"] else "active"
        passes.append(
            {
                "pass": p,
                "state": state,
                "ok": bucket["ok"],
                "failed": bucket["failed"],
                "latency_ms": latency_ms,
            }
        )
    return web.json_response(
        {
            "available": True,
            "doc_id": doc_id,
            "filename": Path(doc["source_path"]).name,
            "passes": passes,
        }
    )


async def handle_eval_pair(request: web.Request) -> web.Response:
    """Return one full eval_pairs row + its judge result for the Eval page comparison body.

    `?pair_id=...` wins; else the first pair for the active run. Both records are
    de-blinded so the frontend doesn't have to know about A/B mapping.
    """
    run_id = _resolve_run_id(request)
    if run_id is None:
        return web.json_response({"available": False})
    pair_id = request.query.get("pair_id")
    if pair_id:
        pair = _read_one(
            "SELECT p.id, p.run_id, p.doc_id, p.datalake_record, p.gpt4_record, p.a_is_datalake, "
            "       r.winner, r.dimension_scores, r.rationale, r.judge_model, "
            "       d.source_path "
            "FROM eval_pairs p LEFT JOIN eval_results r ON r.pair_id=p.id "
            "JOIN documents d ON d.id=p.doc_id WHERE p.id=?",
            (pair_id,),
        )
    else:
        pair = _read_one(
            "SELECT p.id, p.run_id, p.doc_id, p.datalake_record, p.gpt4_record, p.a_is_datalake, "
            "       r.winner, r.dimension_scores, r.rationale, r.judge_model, "
            "       d.source_path "
            "FROM eval_pairs p LEFT JOIN eval_results r ON r.pair_id=p.id "
            "JOIN documents d ON d.id=p.doc_id WHERE p.run_id=? LIMIT 1",
            (run_id,),
        )
    if pair is None:
        return web.json_response({"available": False, "hint": "Run `datalake eval --n 200` to populate eval pairs."})

    datalake_rec = _json_safe(pair["datalake_record"], {})
    gpt4_rec = _json_safe(pair["gpt4_record"], {})

    # winner is A|B|tie — de-blind so we expose a literal "datalake"/"gpt4"/"tie".
    raw_winner = pair["winner"]
    is_dl_a = bool(pair["a_is_datalake"])
    if raw_winner == "tie" or raw_winner is None:
        winner = "tie"
    elif raw_winner == "A":
        winner = "datalake" if is_dl_a else "gpt4"
    else:  # "B"
        winner = "gpt4" if is_dl_a else "datalake"

    # Page count is approximate — derive from text length if recorded, else None.
    page_count = None
    return web.json_response(
        {
            "available": True,
            "pair_id": pair["id"],
            "doc_id": pair["doc_id"],
            "filename": Path(pair["source_path"]).name,
            "page_count": page_count,
            "datalake": _eval_record_view(datalake_rec),
            "gpt4": _eval_record_view(gpt4_rec),
            "winner": winner,
            "judge_model": pair["judge_model"],
            "rationale": pair["rationale"],
            "dimension_scores": _json_safe(pair["dimension_scores"], {}),
        }
    )


def _eval_record_view(rec: dict) -> dict:
    """Flatten the record JSON into the keys the Eval page needs.

    Both pipelines return the same conceptual record (catalog + label); fields are
    nullable because GPT-4's record may be flatter than the agent loop's.
    """
    catalog = rec.get("catalog", {}) if isinstance(rec.get("catalog"), dict) else {}
    label = rec.get("label", {}) if isinstance(rec.get("label"), dict) else {}
    methodology = label.get("methodology", {}) if isinstance(label.get("methodology"), dict) else {}
    structured = label.get("structured_abstract", {}) if isinstance(label.get("structured_abstract"), dict) else {}
    return {
        "content_type": catalog.get("content_type"),
        "summary": structured.get("findings") or structured.get("approach") or "",
        "problem": structured.get("problem", ""),
        "novelty_claim": label.get("novelty_claim", ""),
        "methodology_named": methodology.get("named", []) if isinstance(methodology.get("named"), list) else [],
        "methodology_freetext": methodology.get("other_freetext") or "",
        "domain_tags": label.get("domain_tags", []) if isinstance(label.get("domain_tags"), list) else [],
        "claim_graph": label.get("claim_graph", []) if isinstance(label.get("claim_graph"), list) else [],
    }


async def handle_format_distribution(request: web.Request) -> web.Response:
    """File-extension histogram across this run's documents, normalised to percentages."""
    run_id = _resolve_run_id(request)
    if run_id is None:
        return web.json_response([])
    rows = _read(
        "SELECT source_path FROM documents WHERE run_id=?",
        (run_id,),
    )
    if not rows:
        return web.json_response([])
    counts: dict[str, int] = {}
    for r in rows:
        ext = Path(r["source_path"]).suffix.lstrip(".").upper() or "OTHER"
        counts[ext] = counts.get(ext, 0) + 1
    total = sum(counts.values())
    out = sorted(
        (
            {"label": ext, "count": n, "pct": round(n / total * 100, 1)}
            for ext, n in counts.items()
        ),
        key=lambda r: -r["count"],
    )
    return web.json_response(out)


# ---------------------------------------------------------------------------
# Display helpers — pure functions, no I/O.
# ---------------------------------------------------------------------------


def _humanise_content_type(ct: str) -> str:
    return ct.replace("_", " ").title()


def _humanise_dimension(d: str) -> str:
    return d.replace("_", " ").title()


def _name_from_path(p: str) -> str:
    stem = Path(p).stem
    # Keep arxiv IDs as-is; otherwise title-case the filename for nicer display.
    if stem.replace(".", "").replace("v", "").isdigit():
        return f"arXiv:{stem}"
    return stem.replace("_", " ").replace("-", " ").title()


def _shorten_owner(rationale: str | None) -> str:
    """Pull a short owner string out of the verbose rationale — first ~80 chars works fine."""
    if not rationale:
        return "Unknown"
    first_clause = rationale.split(".")[0].strip()
    return first_clause[:80] + ("…" if len(first_clause) > 80 else "")


def _name_from_corpus(corpus_version: str | None, run_id: str) -> str:
    if corpus_version and corpus_version != "unknown":
        return corpus_version
    return f"run-{run_id[:8]}"


def _empty_counters() -> dict:
    return {
        "docs_done": 0,
        "docs_failed": 0,
        "docs_partial": 0,
        "wafer_usd": 0.0,
        "gpt4_equivalent_usd": 0.0,
        "human_labeler_equivalent_usd": 0.0,
        "avg_overall_confidence": 0.0,
        "cost_ratio_vs_gpt4": None,
        "cost_ratio_vs_human": None,
    }


# ---------------------------------------------------------------------------
# CORS — vite dev is on http://localhost:5173, prod build would be same-origin.
# Open to any localhost origin to avoid having to keep an allowlist in sync.
# ---------------------------------------------------------------------------


@web.middleware
async def cors_middleware(
    request: web.Request, handler: Callable[[web.Request], Any]
) -> web.StreamResponse:
    if request.method == "OPTIONS":
        resp = web.Response(status=204)
    else:
        resp = await handler(request)
    origin = request.headers.get("Origin", "")
    if origin.startswith("http://localhost") or origin.startswith("http://127.0.0.1"):
        resp.headers["Access-Control-Allow-Origin"] = origin
        resp.headers["Access-Control-Allow-Methods"] = "GET, OPTIONS"
        resp.headers["Access-Control-Allow-Headers"] = "Content-Type"
    return resp


def build_app() -> web.Application:
    app = web.Application(middlewares=[cors_middleware])
    app.router.add_get("/api/health", handle_health)
    app.router.add_get("/api/runs", handle_runs)
    app.router.add_get("/api/stream", handle_stream)
    app.router.add_get("/api/catalog", handle_catalog)
    app.router.add_get("/api/runs/recent", handle_recent_uploads)
    app.router.add_get("/api/eval/dimensions", handle_eval_dimensions)
    app.router.add_get("/api/export/sample", handle_export_sample)
    app.router.add_get("/api/counters", handle_counters)
    app.router.add_get("/api/active-trace", handle_active_trace)
    app.router.add_get("/api/eval/pair", handle_eval_pair)
    app.router.add_get("/api/ingestion/format-distribution", handle_format_distribution)
    # Wildcard OPTIONS so the CORS preflight succeeds for any /api/* path.
    app.router.add_route("OPTIONS", "/{tail:.*}", lambda _r: web.Response(status=204))
    return app


def run(host: str = "0.0.0.0", port: int = 8000) -> None:
    web.run_app(build_app(), host=host, port=port, print=None)
