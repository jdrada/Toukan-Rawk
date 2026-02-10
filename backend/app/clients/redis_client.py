"""Redis client for pub/sub event notifications."""

from __future__ import annotations

import json
import logging
from typing import Optional, Any, Dict

import redis.asyncio as redis

from app.config import Settings

logger = logging.getLogger(__name__)


class RedisClient:
    """Redis client for publishing and subscribing to memory events."""

    MEMORY_EVENTS_CHANNEL = "memory:events"

    def __init__(self, settings: Settings) -> None:
        """Initialize Redis client.

        Args:
            settings: Application settings with Redis configuration.
        """
        self.settings = settings
        self._client: Optional[redis.Redis] = None
        self._pubsub: Optional[redis.client.PubSub] = None

    async def connect(self) -> None:
        """Establish connection to Redis."""
        if not self._client:
            self._client = await redis.from_url(
                self.settings.redis_url,
                encoding="utf-8",
                decode_responses=True,
            )
            logger.info("Connected to Redis at %s", self.settings.redis_url)

    async def disconnect(self) -> None:
        """Close Redis connection."""
        if self._pubsub:
            await self._pubsub.close()
            self._pubsub = None

        if self._client:
            await self._client.close()
            self._client = None
            logger.info("Disconnected from Redis")

    async def publish_memory_event(
        self,
        memory_id: str,
        status: str,
        updated_at: str,
    ) -> None:
        """Publish a memory status change event.

        Args:
            memory_id: UUID of the memory that changed.
            status: New status of the memory.
            updated_at: ISO timestamp of when the memory was updated.
        """
        if not self._client:
            await self.connect()

        event_data = {
            "memory_id": memory_id,
            "status": status,
            "updated_at": updated_at,
        }

        try:
            await self._client.publish(
                self.MEMORY_EVENTS_CHANNEL,
                json.dumps(event_data),
            )
            logger.info(
                "[Redis Pub] Memory event: %s (status: %s)",
                memory_id[:8],
                status,
            )
        except Exception as e:
            logger.error("Failed to publish memory event: %s", str(e), exc_info=True)

    async def subscribe_to_memory_events(self) -> redis.client.PubSub:
        """Subscribe to memory events channel.

        Returns:
            PubSub instance subscribed to memory events.
        """
        if not self._client:
            await self.connect()

        self._pubsub = self._client.pubsub()
        await self._pubsub.subscribe(self.MEMORY_EVENTS_CHANNEL)
        logger.info("Subscribed to Redis channel: %s", self.MEMORY_EVENTS_CHANNEL)
        return self._pubsub

    async def get_next_event(self) -> Optional[Dict[str, Any]]:
        """Get the next memory event from the subscription.

        Returns:
            Event data dict or None if no event.
        """
        if not self._pubsub:
            raise RuntimeError("Not subscribed to any channel. Call subscribe_to_memory_events first.")

        message = await self._pubsub.get_message(ignore_subscribe_messages=True, timeout=1.0)
        if message and message["type"] == "message":
            try:
                return json.loads(message["data"])
            except json.JSONDecodeError:
                logger.error("Failed to parse Redis message: %s", message["data"])
                return None
        return None
