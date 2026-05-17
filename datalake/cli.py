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
    run_id: str | None = typer.Option(None, "--run-id"),
    persist: bool = typer.Option(False, "--persist"),
    continue_: bool = typer.Option(False, "--continue", help="Resume after BudgetExceededError."),
    retry_failed: bool = typer.Option(False, "--retry-failed"),
    ceiling: float | None = typer.Option(None, "--ceiling", help="Override wafer_spend_ceiling_usd."),
    debug: bool = typer.Option(False, "--debug"),
    sample_rate: int | None = typer.Option(None, "--sample-rate", help="Override trace_sample_k."),
) -> None:
    """Run the 6-pass agent loop on all INGESTED docs for this run."""
    raise NotImplementedError("TODO: wire to datalake.loop.state_machine")


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
    raise NotImplementedError("TODO: shell out to `streamlit run` with run_id env var")


if __name__ == "__main__":
    app()
