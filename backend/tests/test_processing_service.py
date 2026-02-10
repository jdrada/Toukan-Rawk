"""Tests for ProcessingService (the async pipeline)."""

import pytest
from unittest.mock import AsyncMock
from uuid import UUID

from app.clients.openai import OpenAIClient
from app.clients.s3 import S3Client
from app.exceptions import AIProcessingError, S3UploadError
from app.models.ai import LLMAnalysisResult, TranscriptionResult
from app.repositories.memory_repository import MemoryRepository
from app.services.processing_service import ProcessingService


@pytest.fixture
def processing_service(
    memory_repository: MemoryRepository,
    mock_s3_client: AsyncMock,
    mock_openai_client: AsyncMock,
) -> ProcessingService:
    mock_s3_client._settings = type("S", (), {"s3_bucket_name": "test-bucket"})()
    return ProcessingService(memory_repository, mock_s3_client, mock_openai_client)


class TestProcessMemory:
    @pytest.mark.asyncio
    async def test_happy_path(
        self,
        processing_service: ProcessingService,
        memory_repository: MemoryRepository,
        mock_s3_client: AsyncMock,
        mock_openai_client: AsyncMock,
    ):
        mem = await memory_repository.create(audio_url="s3://test-bucket/audio/test.webm")
        memory_id = UUID(mem.id)

        await processing_service.process_memory(
            memory_id=memory_id,
            audio_url="s3://test-bucket/audio/test.webm",
            correlation_id="corr-123",
        )

        updated = await memory_repository.get_by_id(memory_id)
        assert updated.status == "ready"
        assert updated.transcript is not None
        assert updated.summary is not None
        assert updated.key_points is not None
        assert updated.title is not None

    @pytest.mark.asyncio
    async def test_s3_download_failure(
        self,
        processing_service: ProcessingService,
        memory_repository: MemoryRepository,
        mock_s3_client: AsyncMock,
    ):
        mock_s3_client.get_file.side_effect = S3UploadError(detail="S3 down")

        mem = await memory_repository.create(audio_url="s3://test-bucket/audio/test.webm")
        memory_id = UUID(mem.id)

        await processing_service.process_memory(
            memory_id=memory_id,
            audio_url="s3://test-bucket/audio/test.webm",
            correlation_id="corr-123",
        )

        updated = await memory_repository.get_by_id(memory_id)
        assert updated.status == "failed"
        assert updated.transcript is None

    @pytest.mark.asyncio
    async def test_whisper_failure(
        self,
        processing_service: ProcessingService,
        memory_repository: MemoryRepository,
        mock_openai_client: AsyncMock,
    ):
        mock_openai_client.transcribe_audio.side_effect = AIProcessingError(detail="Whisper down")

        mem = await memory_repository.create(audio_url="s3://test-bucket/audio/test.webm")
        memory_id = UUID(mem.id)

        await processing_service.process_memory(
            memory_id=memory_id,
            audio_url="s3://test-bucket/audio/test.webm",
            correlation_id="corr-123",
        )

        updated = await memory_repository.get_by_id(memory_id)
        assert updated.status == "failed"

    @pytest.mark.asyncio
    async def test_llm_failure_saves_transcript(
        self,
        processing_service: ProcessingService,
        memory_repository: MemoryRepository,
        mock_openai_client: AsyncMock,
    ):
        mock_openai_client.analyze_transcript.side_effect = Exception("LLM exploded")

        mem = await memory_repository.create(audio_url="s3://test-bucket/audio/test.webm")
        memory_id = UUID(mem.id)

        await processing_service.process_memory(
            memory_id=memory_id,
            audio_url="s3://test-bucket/audio/test.webm",
            correlation_id="corr-123",
        )

        updated = await memory_repository.get_by_id(memory_id)
        assert updated.status == "ready"
        assert updated.transcript is not None
        assert updated.summary is None  # LLM failed, no summary
