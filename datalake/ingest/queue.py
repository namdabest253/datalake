"""asyncio.Queue feeder. Pulls INGESTED docs and yields them to the loop runner.

FIFO, no priority — see docs/02-agent-loop.md §Can defer #13.
"""

from __future__ import annotations

import asyncio
from pathlib import Path

from loguru import logger

from datalake.storage.db import connect
from datalake.storage.models import Document

QUEUE_SENTINEL: None = None


async def feed_queue(
    db_path: Path,
    run_id: str,
    queue: asyncio.Queue[Document | None],
) -> None:
    """Stream INGESTED docs into the queue, then close it with a sentinel.

    Text/references are NOT rehydrated here — the loop's READ pass re-reads the
    file from `source_path`. The queue is metadata-only to keep memory bounded
    when feeding 20k-doc demo runs.
    """
    n = 0
    async with connect(db_path) as conn:
        cursor = await conn.execute(
            """
            SELECT id, run_id, source_path, source_hash, content_type_guess,
                   ingested_at, status, partial, timeout
            FROM documents
            WHERE run_id = ? AND status = 'INGESTED'
            ORDER BY ingested_at
            """,
            (run_id,),
        )
        async for row in cursor:
            doc = Document(
                id=row["id"],
                run_id=row["run_id"],
                source_path=row["source_path"],
                source_hash=row["source_hash"],
                content_type_guess=row["content_type_guess"],
                ingested_at=row["ingested_at"],
                status=row["status"],
                partial=bool(row["partial"]),
                timeout=bool(row["timeout"]),
            )
            await queue.put(doc)
            n += 1
        await cursor.close()

    await queue.put(QUEUE_SENTINEL)
    logger.info("queue_feed_done run_id={} docs_enqueued={}", run_id, n)
