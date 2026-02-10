"""Processing router — manually trigger audio processing."""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends

from app.dependencies import get_memory_service
from app.models.memory import UploadResponse
from app.services.memory_service import MemoryService

router = APIRouter(tags=["processing"])


@router.post("/process/{audio_id}", response_model=UploadResponse)
async def trigger_processing(
    audio_id: UUID,
    service: MemoryService = Depends(get_memory_service),
) -> UploadResponse:
    """Manually trigger processing for a memory."""
    return await service.trigger_processing(audio_id)
