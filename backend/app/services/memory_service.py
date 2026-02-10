"""Business logic for memory operations (upload, retrieval, processing trigger)."""

from __future__ import annotations

import logging
from typing import Optional
from uuid import UUID

from fastapi import UploadFile

from app.clients.s3 import S3Client
from app.clients.sqs import SQSClient
from app.exceptions import ResourceNotFoundError, SQSPublishError
from app.models.memory import (
    MemoryListResponse,
    MemoryProcessRequest,
    MemoryResponse,
    MemoryStatus,
    UploadResponse,
)
from app.repositories.memory_repository import MemoryRepository
from app.utils.s3_helpers import generate_s3_key, get_content_type

logger = logging.getLogger(__name__)


class MemoryService:
    """Orchestrates memory upload, retrieval, and processing triggers."""

    def __init__(
        self,
        repository: MemoryRepository,
        s3_client: S3Client,
        sqs_client: SQSClient,
    ) -> None:
        self._repository = repository
        self._s3 = s3_client
        self._sqs = sqs_client

    async def upload_audio(self, file: UploadFile) -> UploadResponse:
        """Upload audio to S3, create DB record, and enqueue processing.

        1. Create a memory record (status=uploading)
        2. Upload file to S3
        3. Update memory with S3 URL
        4. Enqueue SQS processing job
        5. Update status to processing

        If SQS fails, the memory is still saved and can be re-triggered.
        """
        filename = file.filename or "audio.webm"
        file_data = await file.read()

        # Create DB record first
        memory = await self._repository.create(audio_url="")
        memory_id = UUID(memory.id)

        # Upload to S3
        s3_key = generate_s3_key(filename, memory_id)
        content_type = get_content_type(filename)
        audio_url = await self._s3.upload_file(file_data, s3_key, content_type)

        # Update memory with the S3 URL
        memory.audio_url = audio_url
        await self._repository.update_status(memory_id, MemoryStatus.PROCESSING.value)

        # Enqueue processing job (non-fatal if it fails)
        try:
            payload = MemoryProcessRequest(
                memory_id=memory_id,
                audio_url=audio_url,
            )
            await self._sqs.send_message(payload)
        except SQSPublishError:
            logger.warning(
                "SQS enqueue failed for memory %s — can be re-triggered manually",
                memory_id,
            )
            await self._repository.update_status(
                memory_id, MemoryStatus.UPLOADING.value
            )

        return UploadResponse(
            memory_id=memory_id,
            status=MemoryStatus(memory.status),
            message="Audio uploaded and processing enqueued",
        )

    async def get_memory(self, memory_id: UUID) -> MemoryResponse:
        """Get a single memory by ID.

        Raises:
            ResourceNotFoundError: If the memory does not exist.
        """
        memory = await self._repository.get_by_id(memory_id)
        if memory is None:
            raise ResourceNotFoundError(detail=f"Memory {memory_id} not found")
        return MemoryResponse.model_validate(memory)

    async def list_memories(
        self,
        page: int = 1,
        page_size: int = 20,
        search: Optional[str] = None,
        status: Optional[str] = None,
    ) -> MemoryListResponse:
        """List memories with pagination, optional search and status filter."""
        items, total = await self._repository.list_all(
            page=page, page_size=page_size, search=search, status=status,
        )
        return MemoryListResponse(
            items=[MemoryResponse.model_validate(m) for m in items],
            total=total,
            page=page,
            page_size=page_size,
            has_next=(page * page_size) < total,
        )

    async def trigger_processing(self, memory_id: UUID) -> UploadResponse:
        """Manually trigger processing for a memory in uploading/failed state.

        Raises:
            ResourceNotFoundError: If the memory does not exist.
        """
        memory = await self._repository.get_by_id(memory_id)
        if memory is None:
            raise ResourceNotFoundError(detail=f"Memory {memory_id} not found")

        payload = MemoryProcessRequest(
            memory_id=memory_id,
            audio_url=memory.audio_url,
        )
        await self._sqs.send_message(payload)
        await self._repository.update_status(
            memory_id, MemoryStatus.PROCESSING.value
        )

        return UploadResponse(
            memory_id=memory_id,
            status=MemoryStatus.PROCESSING,
            message="Processing re-triggered",
        )
