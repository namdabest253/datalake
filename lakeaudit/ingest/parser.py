"""PyMuPDF wrapper. Extracts text and references from PDFs / text / md / json.

See docs/01-architecture.md (Tech stack) and PRD §8.1.
"""

from __future__ import annotations

import hashlib
from pathlib import Path

from lakeaudit.storage.models import Document


def hash_file(path: Path) -> str:
    """SHA-256 of file contents. Used for idempotent re-runs (UNIQUE(run_id, source_hash))."""
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return f"sha256:{h.hexdigest()}"


def parse_pdf(path: Path) -> tuple[str, list[dict]]:
    """Return (text, references). References are best-effort parsed citations."""
    raise NotImplementedError("TODO: import fitz (PyMuPDF), extract text + references")


def parse_text(path: Path) -> tuple[str, list[dict]]:
    """For .txt and .md inputs."""
    return path.read_text(), []


def parse_json(path: Path) -> tuple[str, list[dict]]:
    """For .json inputs (e.g., NSF grant abstracts in structured form)."""
    raise NotImplementedError("TODO: load and stringify the JSON, extract refs if present")


def guess_content_type(path: Path, snippet: str) -> str:
    """Cheap pre-loop guess from filename + first 200 chars. Refined by the agent loop later."""
    name = path.name.lower()
    if "arxiv" in name or "preprint" in name or "paper" in name:
        return "research_paper"
    if "nsf" in name or "grant" in name or "proposal" in name:
        return "grant_proposal"
    if "dataset" in name:
        return "dataset_description"
    return "other"


async def walk_and_ingest(root: Path, run_id: str) -> list[Document]:
    """Walk root, parse each supported file, return Document objects ready to insert.

    Suffixes accepted: .pdf .txt .md .json. Failed parses return Documents with status=FAILED.
    """
    raise NotImplementedError(
        "TODO: walk root, dispatch on suffix, compute hash, build Document with status=INGESTED."
    )
