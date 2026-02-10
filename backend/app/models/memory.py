"""Pydantic models for the Memory domain."""

from datetime import datetime
from enum import Enum
from typing import List, Optional
from uuid import UUID, uuid4

from pydantic import BaseModel, ConfigDict, Field


class MemoryStatus(str, Enum):
    """Possible states of a memory record."""

    UPLOADING = "uploading"
    PROCESSING = "processing"
    READY = "ready"
    FAILED = "failed"


class MemoryBase(BaseModel):
    """Shared fields for memory models."""

    title: Optional[str] = None


class MemoryCreate(MemoryBase):
    """Internal model used when creating a memory after upload."""

    audio_url: str
    duration: Optional[float] = None


class MemoryResponse(MemoryBase):
    """Response model for a single memory."""

    id: UUID
    audio_url: str
    status: MemoryStatus
    transcript: Optional[str] = None
    summary: Optional[str] = None
    key_points: Optional[List[str]] = None
    action_items: Optional[List[str]] = None
    duration: Optional[float] = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class MemoryListResponse(BaseModel):
    """Paginated list of memories."""

    items: List[MemoryResponse]
    total: int
    page: int
    page_size: int
    has_next: bool


class MemoryProcessRequest(BaseModel):
    """SQS message payload for triggering memory processing."""

    memory_id: UUID
    audio_url: str
    correlation_id: str = Field(default_factory=lambda: str(uuid4()))


class UploadResponse(BaseModel):
    """Response returned after a successful audio upload."""

    memory_id: UUID
    status: MemoryStatus
    message: str
