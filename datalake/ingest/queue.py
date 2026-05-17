"""asyncio.Queue feeder. Pulls INGESTED docs and yields them to the loop runner.

FIFO, no priority — see docs/02-agent-loop.md §Can defer #13.
"""

from __future__ import annotations

import asyncio
from pathlib import Path

from datalake.storage.models import Document


async def feed_queue(
    db_path: Path,
    run_id: str,
    queue: asyncio.Queue[Document],
) -> None:
    """Stream INGESTED docs into the queue, then close it with a sentinel."""
    raise NotImplementedError(
        "TODO: SELECT * FROM documents WHERE run_id=? AND status='INGESTED' ORDER BY ingested_at, "
        "put each on the queue, then put None as sentinel."
    )
