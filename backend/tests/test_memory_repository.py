"""Tests for MemoryRepository against in-memory SQLite."""

import pytest
from uuid import UUID

from app.exceptions import ResourceNotFoundError
from app.repositories.memory_repository import MemoryRepository


class TestMemoryRepository:
    @pytest.mark.asyncio
    async def test_create_returns_memory_with_id(self, memory_repository: MemoryRepository):
        memory = await memory_repository.create(audio_url="s3://bucket/test.webm")
        assert memory.id is not None
        assert memory.audio_url == "s3://bucket/test.webm"
        assert memory.status == "uploading"

    @pytest.mark.asyncio
    async def test_get_by_id_found(self, memory_repository: MemoryRepository):
        memory = await memory_repository.create(audio_url="s3://bucket/test.webm")
        found = await memory_repository.get_by_id(UUID(memory.id))
        assert found is not None
        assert found.id == memory.id

    @pytest.mark.asyncio
    async def test_get_by_id_not_found(self, memory_repository: MemoryRepository):
        result = await memory_repository.get_by_id(UUID("00000000-0000-0000-0000-000000000000"))
        assert result is None

    @pytest.mark.asyncio
    async def test_list_all_empty(self, memory_repository: MemoryRepository):
        items, total = await memory_repository.list_all()
        assert items == []
        assert total == 0

    @pytest.mark.asyncio
    async def test_list_all_with_items(self, memory_repository: MemoryRepository, db_session):
        await memory_repository.create(audio_url="s3://bucket/a.webm")
        await memory_repository.create(audio_url="s3://bucket/b.webm")
        await db_session.flush()

        items, total = await memory_repository.list_all()
        assert total == 2
        assert len(items) == 2

    @pytest.mark.asyncio
    async def test_list_all_pagination(self, memory_repository: MemoryRepository, db_session):
        for i in range(5):
            await memory_repository.create(audio_url=f"s3://bucket/{i}.webm")
        await db_session.flush()

        items, total = await memory_repository.list_all(page=1, page_size=2)
        assert total == 5
        assert len(items) == 2

        items2, _ = await memory_repository.list_all(page=3, page_size=2)
        assert len(items2) == 1  # 5th item on page 3

    @pytest.mark.asyncio
    async def test_list_all_search_by_title(self, memory_repository: MemoryRepository, db_session):
        m1 = await memory_repository.create(audio_url="s3://bucket/a.webm", title="Sprint Planning")
        m2 = await memory_repository.create(audio_url="s3://bucket/b.webm", title="Daily Standup")
        await db_session.flush()

        items, total = await memory_repository.list_all(search="sprint")
        assert total == 1
        assert items[0].title == "Sprint Planning"

    @pytest.mark.asyncio
    async def test_list_all_search_by_summary(self, memory_repository: MemoryRepository, db_session):
        m1 = await memory_repository.create(audio_url="s3://bucket/a.webm")
        m2 = await memory_repository.create(audio_url="s3://bucket/b.webm")
        await db_session.flush()
        await memory_repository.update_processing_results(
            UUID(m1.id), summary="Discussed budget allocation", status="ready",
        )
        await memory_repository.update_processing_results(
            UUID(m2.id), summary="Team building activities", status="ready",
        )
        await db_session.flush()

        items, total = await memory_repository.list_all(search="budget")
        assert total == 1

    @pytest.mark.asyncio
    async def test_list_all_filter_by_status(self, memory_repository: MemoryRepository, db_session):
        m1 = await memory_repository.create(audio_url="s3://bucket/a.webm")
        m2 = await memory_repository.create(audio_url="s3://bucket/b.webm")
        await db_session.flush()
        await memory_repository.update_status(UUID(m1.id), "ready")
        await db_session.flush()

        items, total = await memory_repository.list_all(status="ready")
        assert total == 1
        assert items[0].status == "ready"

    @pytest.mark.asyncio
    async def test_list_all_search_and_status_combined(self, memory_repository: MemoryRepository, db_session):
        m1 = await memory_repository.create(audio_url="s3://bucket/a.webm", title="Sprint Planning")
        m2 = await memory_repository.create(audio_url="s3://bucket/b.webm", title="Sprint Review")
        await db_session.flush()
        await memory_repository.update_status(UUID(m1.id), "ready")
        await db_session.flush()

        # Both match "sprint" but only m1 has status "ready"
        items, total = await memory_repository.list_all(search="sprint", status="ready")
        assert total == 1
        assert items[0].title == "Sprint Planning"

    @pytest.mark.asyncio
    async def test_update_status(self, memory_repository: MemoryRepository):
        memory = await memory_repository.create(audio_url="s3://bucket/test.webm")
        updated = await memory_repository.update_status(UUID(memory.id), "processing")
        assert updated.status == "processing"

    @pytest.mark.asyncio
    async def test_update_status_not_found(self, memory_repository: MemoryRepository):
        with pytest.raises(ResourceNotFoundError):
            await memory_repository.update_status(
                UUID("00000000-0000-0000-0000-000000000000"), "processing"
            )

    @pytest.mark.asyncio
    async def test_update_processing_results(self, memory_repository: MemoryRepository):
        memory = await memory_repository.create(audio_url="s3://bucket/test.webm")
        updated = await memory_repository.update_processing_results(
            UUID(memory.id),
            transcript="Hello world",
            summary="A greeting",
            key_points=["Said hello"],
            action_items=["Wave back"],
            title="Greeting Meeting",
            status="ready",
        )
        assert updated.transcript == "Hello world"
        assert updated.summary == "A greeting"
        assert updated.key_points == ["Said hello"]
        assert updated.action_items == ["Wave back"]
        assert updated.title == "Greeting Meeting"
        assert updated.status == "ready"
