"""Tests for Pydantic models."""

import pytest
from pydantic import ValidationError

from app.models.ai import LLMAnalysisFallback, LLMAnalysisResult, TranscriptionResult
from app.models.memory import (
    MemoryProcessRequest,
    MemoryResponse,
    MemoryStatus,
    UploadResponse,
)


class TestMemoryModels:
    def test_memory_status_values(self):
        assert MemoryStatus.UPLOADING == "uploading"
        assert MemoryStatus.PROCESSING == "processing"
        assert MemoryStatus.READY == "ready"
        assert MemoryStatus.FAILED == "failed"

    def test_memory_process_request_auto_correlation_id(self):
        req = MemoryProcessRequest(
            memory_id="550e8400-e29b-41d4-a716-446655440000",
            audio_url="s3://bucket/key",
        )
        assert req.correlation_id  # auto-generated UUID string
        assert len(req.correlation_id) == 36  # UUID format

    def test_upload_response(self):
        resp = UploadResponse(
            memory_id="550e8400-e29b-41d4-a716-446655440000",
            status=MemoryStatus.PROCESSING,
            message="Audio uploaded",
        )
        assert resp.status == MemoryStatus.PROCESSING


class TestAIModels:
    def test_transcription_result_minimal(self):
        result = TranscriptionResult(text="Hello world")
        assert result.text == "Hello world"
        assert result.language is None
        assert result.duration is None

    def test_transcription_result_full(self):
        result = TranscriptionResult(text="Hola mundo", language="es", duration=45.2)
        assert result.language == "es"
        assert result.duration == 45.2

    def test_llm_analysis_valid(self):
        result = LLMAnalysisResult(
            title="Test Meeting",
            summary="A meeting was held to discuss important topics at length.",
            key_points=["Point 1", "Point 2"],
            action_items=["Action 1"],
        )
        assert result.title == "Test Meeting"
        assert len(result.key_points) == 2

    def test_llm_analysis_empty_key_points_rejected(self):
        with pytest.raises(ValidationError):
            LLMAnalysisResult(
                title="Test",
                summary="A summary that is long enough.",
                key_points=[],
            )

    def test_llm_analysis_short_summary_rejected(self):
        with pytest.raises(ValidationError):
            LLMAnalysisResult(
                title="Test",
                summary="Short",
                key_points=["Point"],
            )

    def test_llm_analysis_action_items_default_empty(self):
        result = LLMAnalysisResult(
            title="Test",
            summary="A summary that is long enough for validation.",
            key_points=["One key point"],
        )
        assert result.action_items == []

    def test_llm_fallback_defaults(self):
        fallback = LLMAnalysisFallback()
        assert fallback.title == "Untitled Memory"
        assert "could not be generated" in fallback.summary
        assert len(fallback.key_points) == 1
        assert fallback.action_items == []
