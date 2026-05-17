"""PyMuPDF wrapper. Extracts text and references from PDFs / text / md / json.

See docs/01-architecture.md (Tech stack) and PRD §8.1.
"""

from __future__ import annotations

import asyncio
import hashlib
import json
import re
import time
import uuid
from pathlib import Path

import fitz  # PyMuPDF
from loguru import logger

from datalake.storage.models import Document

SUPPORTED_SUFFIXES = {".pdf", ".txt", ".md", ".json"}

# Heading that introduces a references / bibliography section in academic docs.
_REFS_HEADING_RE = re.compile(
    r"^\s*(references|bibliography|works\s+cited|citations)\s*$",
    re.IGNORECASE | re.MULTILINE,
)

# Common numbered citation prefixes: "[1]", "1.", "(1)" at the start of a line.
_REF_ENTRY_SPLIT_RE = re.compile(r"\n(?=\s*(?:\[\d+\]|\(\d+\)|\d+\.))")


def hash_file(path: Path) -> str:
    """SHA-256 of file contents. Used for idempotent re-runs (UNIQUE(run_id, source_hash))."""
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return f"sha256:{h.hexdigest()}"


def _extract_references_from_text(text: str) -> list[dict]:
    """Best-effort: find the references section and split into entries."""
    match = _REFS_HEADING_RE.search(text)
    if not match:
        return []
    refs_blob = text[match.end() :].strip()
    if not refs_blob:
        return []
    # Stop at the next obvious section header if one appears (heuristic: ALL-CAPS line).
    end_marker = re.search(r"\n\s*[A-Z][A-Z\s]{4,}\n", refs_blob)
    if end_marker:
        refs_blob = refs_blob[: end_marker.start()]
    parts = _REF_ENTRY_SPLIT_RE.split(refs_blob)
    entries: list[dict] = []
    for part in parts:
        cleaned = " ".join(part.split())
        if len(cleaned) >= 20:  # filter out fragments
            entries.append({"raw": cleaned})
    return entries


def parse_pdf(path: Path) -> tuple[str, list[dict]]:
    """Return (text, references). References are best-effort parsed citations."""
    pages: list[str] = []
    with fitz.open(path) as doc:
        for page in doc:
            pages.append(str(page.get_text("text")))
    text = "\n".join(pages)
    if not text.strip():
        raise ValueError(f"PDF contained no extractable text: {path}")
    return text, _extract_references_from_text(text)


def parse_text(path: Path) -> tuple[str, list[dict]]:
    """For .txt and .md inputs. Best-effort reference extraction same as PDFs."""
    text = path.read_text()
    return text, _extract_references_from_text(text)


def parse_json(path: Path) -> tuple[str, list[dict]]:
    """For .json inputs (e.g., NSF grant abstracts in structured form)."""
    data = json.loads(path.read_text())
    refs_raw = data.pop("references", []) if isinstance(data, dict) else []
    references: list[dict] = []
    for r in refs_raw or []:
        if isinstance(r, dict):
            references.append(r)
        else:
            references.append({"raw": str(r)})
    text = json.dumps(data, indent=2, ensure_ascii=False, sort_keys=True)
    return text, references


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


def _parse_one(path: Path) -> tuple[str, list[dict]]:
    suffix = path.suffix.lower()
    if suffix == ".pdf":
        return parse_pdf(path)
    if suffix in (".txt", ".md"):
        return parse_text(path)
    if suffix == ".json":
        return parse_json(path)
    raise ValueError(f"Unsupported suffix: {suffix}")


def _build_failed_document(path: Path, run_id: str, reason: str) -> Document:
    return Document(
        id=str(uuid.uuid4()),
        run_id=run_id,
        source_path=str(path),
        source_hash=hash_file(path) if path.exists() else f"sha256:missing:{path}",
        content_type_guess=guess_content_type(path, ""),
        ingested_at=time.time(),
        status="FAILED",
        text=None,
        references=[],
    )


def _ingest_one_sync(path: Path, run_id: str) -> Document:
    """Blocking ingest of a single file. Returns a FAILED Document on parse error."""
    try:
        text, references = _parse_one(path)
    except Exception as exc:
        logger.warning("ingest_failed path={} error={}", path, exc)
        return _build_failed_document(path, run_id, str(exc))

    return Document(
        id=str(uuid.uuid4()),
        run_id=run_id,
        source_path=str(path),
        source_hash=hash_file(path),
        content_type_guess=guess_content_type(path, text[:200]),
        ingested_at=time.time(),
        status="INGESTED",
        text=text,
        references=references,
    )


async def walk_and_ingest(root: Path, run_id: str) -> list[Document]:
    """Walk root, parse each supported file, return Document objects ready to insert.

    Suffixes accepted: .pdf .txt .md .json. Failed parses return Documents with status=FAILED.
    """
    root = Path(root)
    if not root.exists():
        raise FileNotFoundError(f"Ingest root does not exist: {root}")

    targets: list[Path]
    if root.is_file():
        targets = [root] if root.suffix.lower() in SUPPORTED_SUFFIXES else []
    else:
        targets = sorted(
            p for p in root.rglob("*") if p.is_file() and p.suffix.lower() in SUPPORTED_SUFFIXES
        )

    if not targets:
        logger.info("ingest_no_files root={}", root)
        return []

    logger.info("ingest_start root={} files={}", root, len(targets))
    docs = await asyncio.gather(*(asyncio.to_thread(_ingest_one_sync, p, run_id) for p in targets))

    n_ok = sum(1 for d in docs if d.status == "INGESTED")
    n_fail = sum(1 for d in docs if d.status == "FAILED")
    logger.info("ingest_done ok={} failed={}", n_ok, n_fail)
    return docs
