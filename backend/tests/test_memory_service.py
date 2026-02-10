"""Tests for MemoryService with mocked AWS clients."""

import io
import pytest
from unittest.mock import AsyncMock
from uuid import UUID

from fastapi import UploadFile

from app.exceptions import ResourceNotFoundError, SQSPublishError
from app.models.memory import MemoryStatus
from app.services.memory_service import MemoryService


class TestUploadAudio:
    @pytest.mark.asyncio
    async def test_upload_creates_memory_and_enqueues(
        self, memory_service: MemoryService, mock_s3_client: AsyncMock, mock_sqs_client: AsyncMock
    ):
        file = UploadFile(filename="meeting.webm", file=io.BytesIO(b"fake-audio"))
        result = await memory_service.upload_audio(file)

        assert result.memory_id is not None
        assert result.status in (MemoryStatus.PROCESSING, MemoryStatus.UPLOADING)
        mock_s3_client.upload_file.assert_called_once()
        mock_sqs_client.send_message.assert_called_once()

    @pytest.mark.asyncio
    async def test_upload_survives_sqs_failure(
        self, memory_service: MemoryService, mock_sqs_client: AsyncMock
    ):
        mock_sqs_client.send_message.side_effect = SQSPublishError(detail="Queue down")

        file = UploadFile(filename="meeting.webm", file=io.BytesIO(b"fake-audio"))
        result = await memory_service.upload_audio(file)

        # Memory is still created — just not enqueued
        assert result.memory_id is not None


class TestGetMemory:
    @pytest.mark.asyncio
    async def test_get_existing_memory(self, memory_service: MemoryService, memory_repository):
        mem = await memory_repository.create(audio_url="s3://bucket/test.webm")
        result = await memory_service.get_memory(UUID(mem.id))
        assert str(result.id) == mem.id

    @pytest.mark.asyncio
    async def test_get_nonexistent_memory_raises(self, memory_service: MemoryService):
        with pytest.raises(ResourceNotFoundError):
            await memory_service.get_memory(UUID("00000000-0000-0000-0000-000000000000"))


class TestListMemories:
    @pytest.mark.asyncio
    async def test_list_empty(self, memory_service: MemoryService):
        result = await memory_service.list_memories()
        assert result.total == 0
        assert result.items == []
        assert result.has_next is False

    @pytest.mark.asyncio
    async def test_list_with_items(self, memory_service: MemoryService, memory_repository, db_session):
        await memory_repository.create(audio_url="s3://bucket/a.webm")
        await memory_repository.create(audio_url="s3://bucket/b.webm")
        await db_session.flush()

        result = await memory_service.list_memories()
        assert result.total == 2
        assert len(result.items) == 2

    @pytest.mark.asyncio
    async def test_list_pagination(self, memory_service: MemoryService, memory_repository, db_session):
        for i in range(5):
            await memory_repository.create(audio_url=f"s3://bucket/{i}.webm")
        await db_session.flush()

        result = await memory_service.list_memories(page=1, page_size=2)
        assert result.total == 5
        assert len(result.items) == 2
        assert result.has_next is True


class TestTriggerProcessing:
    @pytest.mark.asyncio
    async def test_trigger_existing_memory(
        self, memory_service: MemoryService, memory_repository, mock_sqs_client: AsyncMock
    ):
        mem = await memory_repository.create(audio_url="s3://bucket/test.webm")
        result = await memory_service.trigger_processing(UUID(mem.id))
        assert result.status == MemoryStatus.PROCESSING
        mock_sqs_client.send_message.assert_called_once()

    @pytest.mark.asyncio
    async def test_trigger_nonexistent_raises(self, memory_service: MemoryService):
        with pytest.raises(ResourceNotFoundError):
            await memory_service.trigger_processing(UUID("00000000-0000-0000-0000-000000000000"))
