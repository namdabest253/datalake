"""CLI entrypoints. See docs/08-ops-and-demo.md §CLI entrypoints.

Subcommands:
    datalake ingest <path>     Walk a folder, parse PDFs, insert documents.
    datalake run               Run the 6-pass loop on INGESTED docs.
    datalake eval --n 200      Side-by-side Datalake vs single-pass GPT-4.
    datalake export            Emit JSONL + CSV + dataset_card.
    datalake dashboard         Launch the Streamlit UI.
"""

from __future__ import annotations

from pathlib import Path

import typer

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
    raise NotImplementedError("TODO: wire to datalake.ingest.parser + storage.db")


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
