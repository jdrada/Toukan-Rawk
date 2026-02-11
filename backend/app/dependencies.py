"""FastAPI dependency injection wiring.

Composes Settings, DB session, AWS clients, repository, and service
into a clean dependency graph using FastAPI's Depends().
"""

from __future__ import annotations

from collections.abc import AsyncGenerator

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.clients.redis_client import NullRedisClient, RedisClient
from app.clients.s3 import S3Client
from app.clients.sqs import SQSClient
from app.config import Settings, get_settings
from app.repositories.database import get_db_session
from app.repositories.memory_repository import MemoryRepository
from app.services.memory_service import MemoryService


def get_s3_client(
    settings: Settings = Depends(get_settings),
) -> S3Client:
    """Provide an S3Client instance."""
    return S3Client(settings)


def get_sqs_client(
    settings: Settings = Depends(get_settings),
) -> SQSClient:
    """Provide an SQSClient instance."""
    return SQSClient(settings)


def get_redis_client(
    settings: Settings = Depends(get_settings),
) -> RedisClient:
    """Provide a RedisClient or NullRedisClient based on settings."""
    if not settings.redis_enabled:
        return NullRedisClient()
    return RedisClient(settings)


def get_memory_repository(
    session: AsyncSession = Depends(get_db_session),
) -> MemoryRepository:
    """Provide a MemoryRepository instance."""
    return MemoryRepository(session)


def get_memory_service(
    repository: MemoryRepository = Depends(get_memory_repository),
    s3_client: S3Client = Depends(get_s3_client),
    sqs_client: SQSClient = Depends(get_sqs_client),
    redis_client: RedisClient = Depends(get_redis_client),
) -> MemoryService:
    """Provide a fully-wired MemoryService instance."""
    return MemoryService(repository, s3_client, sqs_client, redis_client)
