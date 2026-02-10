"""Async database access layer for Memory records."""

from __future__ import annotations

from typing import List, Optional, Tuple
from uuid import UUID

from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.exceptions import ResourceNotFoundError
from app.repositories.models import MemoryORM


class MemoryRepository:
    """All database operations for the memories table."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create(
        self,
        audio_url: str,
        title: Optional[str] = None,
        duration: Optional[float] = None,
    ) -> MemoryORM:
        """Create a new memory record with status 'uploading'."""
        memory = MemoryORM(
            audio_url=audio_url,
            title=title,
            duration=duration,
            status="uploading",
        )
        self._session.add(memory)
        await self._session.flush()
        return memory

    async def get_by_id(self, memory_id: UUID) -> Optional[MemoryORM]:
        """Get a memory by ID, or None if not found."""
        stmt = select(MemoryORM).where(MemoryORM.id == str(memory_id))
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

    async def list_all(
        self,
        page: int = 1,
        page_size: int = 20,
        search: Optional[str] = None,
        status: Optional[str] = None,
    ) -> Tuple[List[MemoryORM], int]:
        """Return a paginated list of memories and the total count.

        Args:
            search: ILIKE filter on title and summary columns.
            status: Exact match filter on status column.
        """
        base = select(MemoryORM)

        if search:
            pattern = f"%{search}%"
            base = base.where(
                or_(
                    MemoryORM.title.ilike(pattern),
                    MemoryORM.summary.ilike(pattern),
                )
            )
        if status:
            base = base.where(MemoryORM.status == status)

        # Total count
        count_stmt = select(func.count()).select_from(base.subquery())
        total_result = await self._session.execute(count_stmt)
        total = total_result.scalar_one()

        # Paginated results
        offset = (page - 1) * page_size
        stmt = base.order_by(MemoryORM.created_at.desc()).offset(offset).limit(page_size)
        result = await self._session.execute(stmt)
        items = list(result.scalars().all())

        return items, total

    async def update_status(self, memory_id: UUID, status: str) -> MemoryORM:
        """Update the status of a memory. Raises ResourceNotFoundError if not found."""
        memory = await self.get_by_id(memory_id)
        if memory is None:
            raise ResourceNotFoundError(detail=f"Memory {memory_id} not found")
        memory.status = status
        await self._session.flush()
        return memory

    async def update_processing_results(
        self,
        memory_id: UUID,
        *,
        transcript: Optional[str] = None,
        summary: Optional[str] = None,
        key_points: Optional[List[str]] = None,
        action_items: Optional[List[str]] = None,
        title: Optional[str] = None,
        status: str = "ready",
    ) -> MemoryORM:
        """Save processing results (transcript, summary, etc.) to a memory."""
        memory = await self.get_by_id(memory_id)
        if memory is None:
            raise ResourceNotFoundError(detail=f"Memory {memory_id} not found")

        if transcript is not None:
            memory.transcript = transcript
        if summary is not None:
            memory.summary = summary
        if key_points is not None:
            memory.key_points = key_points
        if action_items is not None:
            memory.action_items = action_items
        if title is not None:
            memory.title = title
        memory.status = status

        await self._session.flush()
        return memory

    async def delete(self, memory_id: UUID) -> None:
        """Delete a memory by ID. Raises ResourceNotFoundError if not found."""
        memory = await self.get_by_id(memory_id)
        if memory is None:
            raise ResourceNotFoundError(detail=f"Memory {memory_id} not found")
        await self._session.delete(memory)
        await self._session.flush()
