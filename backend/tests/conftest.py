"""Shared test fixtures for the RAWK backend test suite."""

from __future__ import annotations

from typing import AsyncGenerator
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from app.clients.openai import OpenAIClient
from app.clients.s3 import S3Client
from app.clients.sqs import SQSClient
from app.config import Settings
from app.dependencies import (
    get_db_session,
    get_memory_service,
    get_s3_client,
    get_settings,
    get_sqs_client,
)
from app.main import app
from app.models.ai import LLMAnalysisResult, TranscriptionResult
from app.repositories.database import Base
from app.repositories.memory_repository import MemoryRepository
from app.services.memory_service import MemoryService


@pytest.fixture
def settings() -> Settings:
    """Test settings with dummy values."""
    return Settings(
        aws_region="us-east-1",
        aws_access_key_id="test-key",
        aws_secret_access_key="test-secret",
        s3_bucket_name="test-bucket",
        sqs_queue_url="https://sqs.us-east-1.amazonaws.com/123/test-queue",
        db_host="localhost",
        db_name="test_db",
        openai_api_key="sk-test",
        environment="test",
        debug=False,
    )


@pytest.fixture
async def db_engine():
    """Create an in-memory SQLite async engine for testing."""
    engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield engine
    await engine.dispose()


@pytest.fixture
async def db_session(db_engine) -> AsyncGenerator[AsyncSession, None]:
    """Yield an async session bound to the in-memory SQLite engine."""
    factory = async_sessionmaker(db_engine, class_=AsyncSession, expire_on_commit=False)
    async with factory() as session:
        yield session


@pytest.fixture
def memory_repository(db_session: AsyncSession) -> MemoryRepository:
    """Provide a MemoryRepository backed by the test DB session."""
    return MemoryRepository(db_session)


@pytest.fixture
def mock_s3_client() -> AsyncMock:
    """Mocked S3Client."""
    client = AsyncMock(spec=S3Client)
    client.upload_file.return_value = "s3://test-bucket/audio/test.webm"
    client.get_file.return_value = b"fake-audio-bytes"
    client.generate_presigned_url.return_value = "https://test-bucket.s3.amazonaws.com/audio/test.webm?signed"
    return client


@pytest.fixture
def mock_sqs_client() -> AsyncMock:
    """Mocked SQSClient."""
    client = AsyncMock(spec=SQSClient)
    client.send_message.return_value = "msg-id-123"
    return client


@pytest.fixture
def mock_openai_client() -> AsyncMock:
    """Mocked OpenAIClient."""
    client = AsyncMock(spec=OpenAIClient)
    client.transcribe_audio.return_value = TranscriptionResult(
        text="Hello, this is a test meeting about project planning.",
        language="en",
        duration=30.0,
    )
    client.analyze_transcript.return_value = LLMAnalysisResult(
        title="Project Planning Meeting",
        summary="The team discussed project planning and upcoming milestones for the quarter.",
        key_points=["Discussed Q1 milestones", "Reviewed sprint backlog"],
        action_items=["Create task board", "Schedule follow-up"],
    )
    return client


@pytest.fixture
def memory_service(
    memory_repository: MemoryRepository,
    mock_s3_client: AsyncMock,
    mock_sqs_client: AsyncMock,
) -> MemoryService:
    """Provide a MemoryService with real repo and mocked AWS clients."""
    return MemoryService(memory_repository, mock_s3_client, mock_sqs_client)


@pytest.fixture
async def async_client(
    db_session: AsyncSession,
    mock_s3_client: AsyncMock,
    mock_sqs_client: AsyncMock,
    settings: Settings,
) -> AsyncGenerator[AsyncClient, None]:
    """FastAPI async test client with dependency overrides."""
    repository = MemoryRepository(db_session)
    service = MemoryService(repository, mock_s3_client, mock_sqs_client)

    app.dependency_overrides[get_settings] = lambda: settings
    app.dependency_overrides[get_db_session] = lambda: db_session
    app.dependency_overrides[get_s3_client] = lambda: mock_s3_client
    app.dependency_overrides[get_sqs_client] = lambda: mock_sqs_client
    app.dependency_overrides[get_memory_service] = lambda: service

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        yield client

    app.dependency_overrides.clear()
