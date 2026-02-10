"""Memories router — list and retrieve memories."""

from __future__ import annotations

from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, Query

from app.dependencies import get_memory_service
from app.models.memory import MemoryListResponse, MemoryResponse
from app.services.memory_service import MemoryService

router = APIRouter(prefix="/memories", tags=["memories"])


@router.get("", response_model=MemoryListResponse)
async def list_memories(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    search: Optional[str] = Query(default=None, min_length=1, max_length=200),
    status: Optional[str] = Query(default=None),
    service: MemoryService = Depends(get_memory_service),
) -> MemoryListResponse:
    """List all memories with pagination, optional search and status filter."""
    return await service.list_memories(
        page=page, page_size=page_size, search=search, status=status,
    )


@router.get("/{memory_id}", response_model=MemoryResponse)
async def get_memory(
    memory_id: UUID,
    service: MemoryService = Depends(get_memory_service),
) -> MemoryResponse:
    """Get a single memory by ID."""
    return await service.get_memory(memory_id)
