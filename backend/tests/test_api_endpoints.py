"""Integration tests for FastAPI endpoints."""

import pytest
from httpx import AsyncClient


class TestHealthEndpoint:
    @pytest.mark.asyncio
    async def test_health_returns_200(self, async_client: AsyncClient):
        response = await async_client.get("/health")
        assert response.status_code == 200
        assert response.json() == {"status": "ok", "service": "rawk-backend"}


class TestRootEndpoint:
    @pytest.mark.asyncio
    async def test_root_returns_service_info(self, async_client: AsyncClient):
        response = await async_client.get("/")
        assert response.status_code == 200
        data = response.json()
        assert data["service"] == "RAWK Backend"
        assert "upload" in data["endpoints"]


class TestUploadEndpoint:
    @pytest.mark.asyncio
    async def test_upload_without_file_returns_422(self, async_client: AsyncClient):
        response = await async_client.post("/upload")
        assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_upload_with_file_returns_201(self, async_client: AsyncClient):
        response = await async_client.post(
            "/upload",
            files={"file": ("meeting.webm", b"fake-audio-data", "audio/webm")},
        )
        assert response.status_code == 201
        data = response.json()
        assert "memory_id" in data
        assert data["message"] == "Audio uploaded and processing enqueued"


class TestMemoriesEndpoint:
    @pytest.mark.asyncio
    async def test_list_empty(self, async_client: AsyncClient):
        response = await async_client.get("/memories")
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 0
        assert data["items"] == []

    @pytest.mark.asyncio
    async def test_list_after_upload(self, async_client: AsyncClient):
        # Upload first
        await async_client.post(
            "/upload",
            files={"file": ("test.webm", b"audio", "audio/webm")},
        )
        response = await async_client.get("/memories")
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 1

    @pytest.mark.asyncio
    async def test_get_memory_by_id(self, async_client: AsyncClient):
        # Upload first
        upload_resp = await async_client.post(
            "/upload",
            files={"file": ("test.webm", b"audio", "audio/webm")},
        )
        memory_id = upload_resp.json()["memory_id"]

        response = await async_client.get(f"/memories/{memory_id}")
        assert response.status_code == 200
        assert response.json()["id"] == memory_id

    @pytest.mark.asyncio
    async def test_list_with_search_param(self, async_client: AsyncClient):
        response = await async_client.get("/memories", params={"search": "test"})
        assert response.status_code == 200
        data = response.json()
        assert "items" in data

    @pytest.mark.asyncio
    async def test_list_with_status_filter(self, async_client: AsyncClient):
        response = await async_client.get("/memories", params={"status": "ready"})
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 0

    @pytest.mark.asyncio
    async def test_get_nonexistent_memory_returns_404(self, async_client: AsyncClient):
        response = await async_client.get("/memories/00000000-0000-0000-0000-000000000000")
        assert response.status_code == 404


class TestProcessEndpoint:
    @pytest.mark.asyncio
    async def test_trigger_nonexistent_returns_404(self, async_client: AsyncClient):
        response = await async_client.post("/process/00000000-0000-0000-0000-000000000000")
        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_trigger_existing_memory(self, async_client: AsyncClient):
        upload_resp = await async_client.post(
            "/upload",
            files={"file": ("test.webm", b"audio", "audio/webm")},
        )
        memory_id = upload_resp.json()["memory_id"]

        response = await async_client.post(f"/process/{memory_id}")
        assert response.status_code == 200
        assert response.json()["status"] == "processing"
