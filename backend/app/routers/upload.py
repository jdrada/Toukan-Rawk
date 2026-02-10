"""Upload router — handles audio file uploads."""

from __future__ import annotations

from fastapi import APIRouter, Depends, File, UploadFile

from app.dependencies import get_memory_service
from app.models.memory import UploadResponse
from app.services.memory_service import MemoryService

router = APIRouter(tags=["upload"])


@router.post("/upload", response_model=UploadResponse, status_code=201)
async def upload_audio(
    file: UploadFile = File(...),
    service: MemoryService = Depends(get_memory_service),
) -> UploadResponse:
    """Upload an audio file for processing."""
    return await service.upload_audio(file)
