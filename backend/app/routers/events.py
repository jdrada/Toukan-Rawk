"""Server-Sent Events (SSE) router for real-time memory status updates."""

from __future__ import annotations

import asyncio
import json
import logging
from collections.abc import AsyncGenerator

from fastapi import APIRouter
from fastapi.responses import StreamingResponse

from app.clients.redis_client import RedisClient
from app.config import Settings

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/events", tags=["events"])


async def memory_status_stream() -> AsyncGenerator[str, None]:
    """Generate Server-Sent Events for memory status updates.

    Subscribes to Redis channel for real-time memory events.
    Sends keepalive events every 30 seconds.
    """
    settings = Settings()
    redis_client = RedisClient(settings)

    try:
        # Connect and subscribe to Redis
        await redis_client.connect()
        pubsub = await redis_client.subscribe_to_memory_events()
        logger.info("SSE client subscribed to Redis memory events")

        last_keepalive = asyncio.get_event_loop().time()
        keepalive_interval = 30.0

        while True:
            current_time = asyncio.get_event_loop().time()

            # Try to get next event from Redis (non-blocking with 1s timeout)
            try:
                event_data = await redis_client.get_next_event()

                if event_data:
                    # Forward Redis event to SSE client
                    yield f"event: memory-update\n"
                    yield f"data: {json.dumps(event_data)}\n\n"
                    logger.debug(
                        "[Redis Sub] Forwarded event: %s (status: %s)",
                        event_data.get("memory_id", "unknown")[:8],
                        event_data.get("status", "unknown"),
                    )
                    last_keepalive = current_time

            except Exception as e:
                # Log error but don't break the stream
                logger.error("Error getting Redis event: %s", str(e), exc_info=True)

            # Send keepalive if needed
            if current_time - last_keepalive >= keepalive_interval:
                yield f": keepalive\n\n"
                last_keepalive = current_time
                logger.debug("Sent SSE keepalive")

    except asyncio.CancelledError:
        logger.info("SSE stream cancelled by client disconnect")
        raise
    except Exception as e:
        logger.error("Unexpected error in SSE stream: %s", str(e), exc_info=True)
        raise
    finally:
        # Clean up Redis connection
        await redis_client.disconnect()
        logger.info("SSE client disconnected from Redis")


@router.get("/memories")
async def stream_memory_events() -> StreamingResponse:
    """Stream real-time memory status updates via Server-Sent Events.

    Connects to Redis Pub/Sub and receives events when memory status changes.

    Event format:
        event: memory-update
        data: {"memory_id": "...", "status": "processing", "updated_at": "..."}

    The stream also sends keepalive comments every 30 seconds.
    """
    return StreamingResponse(
        memory_status_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",  # Disable nginx buffering
        },
    )
