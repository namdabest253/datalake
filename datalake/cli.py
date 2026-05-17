"""CLI entrypoints. See docs/08-ops-and-demo.md §CLI entrypoints.

Subcommands:
    datalake ingest <path>     Walk a folder, parse PDFs, insert documents.
    datalake run               Run the 6-pass loop on INGESTED docs.
    datalake eval --n 200      Side-by-side Datalake vs single-pass GPT-4.
    datalake export            Emit JSONL + CSV + dataset_card.
    datalake dashboard         Launch the Streamlit UI.
"""

from __future__ import annotations

import asyncio
from pathlib import Path

import typer
from loguru import logger

from datalake.config import load_settings
from datalake.ingest.parser import walk_and_ingest
from datalake.storage.db import init_db
from datalake.storage.models import Document
from datalake.storage.writes import insert_documents, insert_run

app = typer.Typer(
    name="datalake",
    help="Agentic data-prep system for universities. See docs/00-overview.md.",
    no_args_is_help=True,
)


@app.command()
def ingest(
    path: Path = typer.Argument(..., exists=True, help="Folder of PDFs / text / JSON."),
    run_id: str | None = typer.Option(None, "--run-id"),
    persist: bool = typer.Option(False, "--persist", help="Keep existing SQLite schema."),
) -> None:
    """Walk a folder, parse documents, insert into the documents table."""
    settings = load_settings()
    db_path = settings.paths.sqlite_db

    async def _go() -> None:
        await init_db(db_path, persist=persist)
        rid = await insert_run(db_path, settings, path, run_id=run_id)
        docs = await walk_and_ingest(path, run_id=rid)
        n_ok = sum(1 for d in docs if d.status == "INGESTED")
        n_failed = sum(1 for d in docs if d.status == "FAILED")
        written = await insert_documents(db_path, docs)
        logger.info(
            "ingest_complete run_id={} db={} parsed_ok={} parsed_failed={} rows_written={}",
            rid,
            db_path,
            n_ok,
            n_failed,
            written,
        )
        typer.echo(f"run_id={rid}  parsed_ok={n_ok}  failed={n_failed}  rows={written}")

    asyncio.run(_go())


@app.command()
def run(
    run_id: str | None = typer.Option(None, "--run-id", help="Defaults to the most recent run."),
    limit: int | None = typer.Option(None, "--limit", help="Cap docs processed (testing)."),
    ceiling: float | None = typer.Option(None, "--ceiling", help="Override wafer_spend_ceiling_usd."),
    debug: bool = typer.Option(False, "--debug"),
) -> None:
    """Run the 6-pass agent loop on INGESTED docs for this run."""
    import sys

    from datalake.inference.accounting import BudgetExceededError
    from datalake.inference.base import GlobalSemaphores
    from datalake.inference.wafer import WaferClient
    from datalake.ingest.parser import _parse_one
    from datalake.loop.state_machine import run_doc
    from datalake.storage.db import connect

    settings = load_settings()
    if ceiling is not None:
        settings = settings.model_copy(update={"wafer_spend_ceiling_usd": ceiling})
    if not settings.wafer_api_key:
        typer.echo("ERROR: WAFER_API_KEY not set. Configure .env.", err=True)
        raise typer.Exit(1)

    if debug:
        logger.remove()
        logger.add(sys.stderr, level="DEBUG")

    db_path = settings.paths.sqlite_db
    if not db_path.exists():
        typer.echo(f"ERROR: no DB at {db_path}. Run `datalake ingest <path>` first.", err=True)
        raise typer.Exit(1)

    heuristics_yaml = (
        settings.paths.heuristics.read_text() if settings.paths.heuristics.exists() else ""
    )

    async def _go() -> None:
        sems = GlobalSemaphores(
            wafer=settings.wafer_concurrency,
            openai=settings.openai_concurrency,
            judge=settings.judge_concurrency,
        )
        client = WaferClient(
            api_key=settings.wafer_api_key,
            base_url=settings.wafer_base_url,
            model=settings.wafer_loop_model,
            semaphores=sems,
        )
        per_doc_sem = asyncio.Semaphore(settings.per_doc_concurrency)

        async with connect(db_path) as conn:
            # Resolve run_id (default = most recent run).
            resolved = run_id
            if resolved is None:
                row = await (await conn.execute(
                    "SELECT id FROM runs ORDER BY started_at DESC LIMIT 1"
                )).fetchone()
                if row is None:
                    typer.echo("ERROR: no runs in DB. Run `datalake ingest <path>` first.", err=True)
                    raise typer.Exit(1)
                resolved = row[0]

            sql = (
                "SELECT id, source_path, source_hash, content_type_guess, ingested_at "
                "FROM documents WHERE run_id=? AND status='INGESTED' ORDER BY ingested_at"
            )
            params: tuple = (resolved,)
            if limit is not None:
                sql += " LIMIT ?"
                params = (resolved, limit)
            rows = await (await conn.execute(sql, params)).fetchall()

            if not rows:
                typer.echo(f"No INGESTED docs for run_id={resolved}.", err=True)
                return

            typer.echo(f"run_id={resolved}  processing {len(rows)} docs...")
            stats = {"done": 0, "partial": 0, "failed": 0, "wafer_micro_usd": 0}

            async def _process(row: object) -> None:
                row_dict = dict(row)
                try:
                    text, refs = _parse_one(Path(row_dict["source_path"]))
                except Exception as exc:  # noqa: BLE001
                    logger.warning(f"re-parse failed for {row_dict['source_path']}: {exc}")
                    stats["failed"] += 1
                    return
                doc = Document(
                    id=row_dict["id"],
                    run_id=resolved,
                    source_path=row_dict["source_path"],
                    source_hash=row_dict["source_hash"],
                    content_type_guess=row_dict["content_type_guess"],
                    ingested_at=row_dict["ingested_at"],
                    status="INGESTED",
                    text=text,
                    references=refs,
                )
                result = await run_doc(
                    doc, 0, client, heuristics_yaml, settings, per_doc_sem,
                    conn=conn, run_id=resolved,
                )
                if result.partial:
                    stats["partial"] += 1
                elif str(result.state) == "FAILED":
                    stats["failed"] += 1
                else:
                    stats["done"] += 1
                stats["wafer_micro_usd"] += result.wafer_micro_usd

            try:
                # Single connection → process sequentially to avoid SQLite write contention.
                # For real fan-out across docs, use multiple connections; out of scope here.
                for row in rows:
                    await _process(row)
            except BudgetExceededError as e:
                typer.echo(f"PAUSED: {e}", err=True)

            typer.echo(
                f"done={stats['done']}  partial={stats['partial']}  failed={stats['failed']}  "
                f"wafer_spend=${stats['wafer_micro_usd'] / 1_000_000:.4f}"
            )

    asyncio.run(_go())


@app.command(name="eval")
def eval_cmd(
    n: int = typer.Option(200, "--n"),
    run_id: str | None = typer.Option(None, "--run-id"),
    dry_run: bool = typer.Option(False, "--dry-run"),
    judge_model: str | None = typer.Option(None, "--judge-model"),
) -> None:
    """Run the side-by-side eval. GPT-4 actually executes here."""
    raise NotImplementedError("TODO: wire to datalake.eval.harness")


@app.command()
def export(
    run_id: str | None = typer.Option(None, "--run-id"),
    out: Path = typer.Option(Path("./.datalake/export"), "--out"),
) -> None:
    """Emit JSONL + catalog CSV + dataset_card.md."""
    raise NotImplementedError("TODO: wire to datalake.export.jsonl/csv/dataset_card")


@app.command()
def dashboard(
    run_id: str | None = typer.Option(None, "--run-id"),
    port: int = typer.Option(8501, "--port"),
) -> None:
    """Launch the Streamlit UI. Thin wrapper over `streamlit run datalake/dashboard/app.py`."""
    import os
    import subprocess
    import sys

    app_path = Path(__file__).parent / "dashboard" / "app.py"
    env = os.environ.copy()
    if run_id:
        env["DATALAKE_RUN_ID"] = run_id
    cmd = [
        sys.executable,
        "-m",
        "streamlit",
        "run",
        str(app_path),
        "--server.port",
        str(port),
        "--server.headless",
        "true",
        "--browser.gatherUsageStats",
        "false",
    ]
    logger.info("dashboard_launch run_id={} port={}", run_id or "<latest>", port)
    subprocess.run(cmd, env=env, check=False)


if __name__ == "__main__":
    app()
