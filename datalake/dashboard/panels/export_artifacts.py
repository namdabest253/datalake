"""Panel 7 (off-spec extension): Export-artifact strip.

Surfaces the JSONL / catalog CSV / dataset_card.md produced by `datalake export`.
If artifacts haven't been generated yet for this run, shows a one-line CLI hint
so the judge or operator knows the next step. Not part of docs/06; bolted on so
the demo loop (run → export → look at it) is complete without leaving the UI.
"""

from __future__ import annotations

from pathlib import Path

import streamlit as st

from datalake.config import load_settings

_EXTENSIONS = [
    ("jsonl", "{run}.jsonl", "JSONL (HF-compatible)"),
    ("csv", "{run}-catalog.csv", "Catalog CSV"),
    ("md", "{run}-dataset_card.md", "Dataset card"),
]

_MIME_TYPES = {"jsonl": "application/x-ndjson", "csv": "text/csv", "md": "text/markdown"}


def _export_dir() -> Path:
    """Mirror the CLI default; if `datalake export --out` was overridden, hint at that."""
    return Path("./.datalake/export")


def render(run_id: str) -> None:
    st.subheader("7. Export artifacts")

    out_dir = _export_dir()
    if not out_dir.exists():
        st.caption(
            f"No artifacts directory at `{out_dir}`. "
            "Run `datalake export` after the loop completes."
        )
        return

    found = [(ext, label, out_dir / name.format(run=run_id)) for ext, name, label in _EXTENSIONS]
    present = [(ext, label, path) for ext, label, path in found if path.exists()]

    if not present:
        # Surface other runs' files so the operator knows the dir isn't empty.
        siblings = sorted(p.name for p in out_dir.iterdir() if p.is_file())[:5]
        hint = f" (other files present: {', '.join(siblings)})" if siblings else ""
        st.caption(
            f"No artifacts for run `{run_id[:8]}…` yet.{hint}  "
            "Run `datalake export` to generate them."
        )
        return

    cols = st.columns(len(present))
    settings = load_settings()  # noqa: F841 — touched so import isn't dead if Settings grows hooks
    for col, (ext, label, path) in zip(cols, present, strict=False):
        with col:
            size_kb = path.stat().st_size / 1024
            st.metric(label, f"{size_kb:,.1f} KB")
            with path.open("rb") as fh:
                st.download_button(
                    label=f"Download .{ext}",
                    data=fh.read(),
                    file_name=path.name,
                    mime=_MIME_TYPES.get(ext, "application/octet-stream"),
                    use_container_width=True,
                )

    # Inline a peek at the dataset card so judges don't have to download it to see the summary.
    card_path = next((p for ext, _, p in present if ext == "md"), None)
    if card_path is not None:
        with st.expander("Preview dataset_card.md", expanded=False):
            st.markdown(card_path.read_text(encoding="utf-8"))
