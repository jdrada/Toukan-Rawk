"""Server-Sent Events (SSE) router for real-time memory status updates."""

from __future__ import annotations

import asyncio
import json
import logging
from collections.abc import AsyncGenerator
from typing import Optional

from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse

from app.dependencies import get_memory_repository
from app.repositories.memory_repository import MemoryRepository

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/events", tags=["events"])


async def memory_status_stream(
    repository: MemoryRepository,
) -> AsyncGenerator[str, None]:
    """Generate Server-Sent Events for memory status updates.

    Polls database every 2 seconds for memories with status 'uploading' or 'processing'.
    Sends keepalive events every 30 seconds.
    """
    last_keepalive = asyncio.get_event_loop().time()
    keepalive_interval = 30.0
    poll_interval = 2.0

    try:
        while True:
            current_time = asyncio.get_event_loop().time()

            # Query for active memories
            try:
                uploading_memories, _ = await repository.list_all(
                    page=1,
                    page_size=100,
                    status="uploading",
                )
                processing_memories, _ = await repository.list_all(
                    page=1,
                    page_size=100,
                    status="processing",
                )

                active_memories = uploading_memories + processing_memories

                # Send event for each active memory
                for memory in active_memories:
                    event_data = {
                        "memory_id": str(memory.id),
                        "status": memory.status,
                    }
                    yield f"event: memory-update\n"
                    yield f"data: {json.dumps(event_data)}\n\n"
                    logger.debug("Sent SSE update for memory %s: %s", memory.id, memory.status)

                # Update keepalive timer if we sent events
                if active_memories:
                    last_keepalive = current_time

            except Exception as e:
                # Log error but don't break the stream
                logger.error("Error querying memories for SSE: %s", str(e), exc_info=True)

            # Send keepalive if needed
            if current_time - last_keepalive >= keepalive_interval:
                yield f": keepalive\n\n"
                last_keepalive = current_time
                logger.debug("Sent SSE keepalive")

            # Wait before next poll
            await asyncio.sleep(poll_interval)

    except asyncio.CancelledError:
        logger.info("SSE stream cancelled by client disconnect")
        raise
    except Exception as e:
        logger.error("Unexpected error in SSE stream: %s", str(e), exc_info=True)
        raise


@router.get("/memories")
async def stream_memory_events(
    repository: MemoryRepository = Depends(get_memory_repository),
) -> StreamingResponse:
    """Stream real-time memory status updates via Server-Sent Events.

    Connects to the SSE endpoint and receives events when memories are
    in 'uploading' or 'processing' status.

    Event format:
        event: memory-update
        data: {"memory_id": "...", "status": "processing"}

    The stream also sends keepalive comments every 30 seconds.
    """
    return StreamingResponse(
        memory_status_stream(repository),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",  # Disable nginx buffering
        },
    )
