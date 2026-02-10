"""Processing pipeline: download audio, transcribe, analyze, save results."""

from __future__ import annotations

import logging
from uuid import UUID

from app.clients.openai import OpenAIClient
from app.clients.s3 import S3Client
from app.exceptions import AIProcessingError, S3UploadError
from app.models.memory import MemoryStatus
from app.repositories.memory_repository import MemoryRepository

logger = logging.getLogger(__name__)


class ProcessingService:
    """Orchestrates the full async processing pipeline for a memory."""

    def __init__(
        self,
        repository: MemoryRepository,
        s3_client: S3Client,
        openai_client: OpenAIClient,
    ) -> None:
        self._repository = repository
        self._s3 = s3_client
        self._openai = openai_client

    async def process_memory(
        self,
        memory_id: UUID,
        audio_url: str,
        correlation_id: str,
    ) -> None:
        """Run the full processing pipeline for a memory.

        Pipeline:
            1. Update status to "processing"
            2. Download audio from S3
            3. Transcribe with Whisper
            4. Analyze transcript with LLM
            5. Save results to database
            6. Update status to "ready"

        Fallbacks:
            - Whisper fails: status → "failed", audio preserved in S3
            - LLM fails: transcript saved, summary=None, status → "ready"

        Args:
            memory_id: UUID of the memory to process.
            audio_url: S3 URL of the audio file.
            correlation_id: Tracing ID from the SQS message.
        """
        log_ctx = f"memory_id={memory_id}, correlation_id={correlation_id}"
        logger.info("Processing started: %s", log_ctx)

        # 1. Update status
        await self._repository.update_status(memory_id, MemoryStatus.PROCESSING.value)

        # 2. Download audio from S3
        s3_key = audio_url.replace(f"s3://{self._s3._settings.s3_bucket_name}/", "")
        try:
            audio_data = await self._s3.get_file(s3_key)
            logger.info("Audio downloaded: %s (%d bytes)", log_ctx, len(audio_data))
        except S3UploadError as exc:
            logger.error("Audio download failed: %s — %s", log_ctx, exc)
            await self._repository.update_status(
                memory_id, MemoryStatus.FAILED.value
            )
            return

        # 3. Transcribe with Whisper
        try:
            transcription = await self._openai.transcribe_audio(audio_data)
            logger.info(
                "Transcription complete: %s (%d chars)",
                log_ctx,
                len(transcription.text),
            )
        except AIProcessingError as exc:
            logger.error("Transcription failed: %s — %s", log_ctx, exc)
            await self._repository.update_status(
                memory_id, MemoryStatus.FAILED.value
            )
            return

        # 4. Analyze transcript with LLM
        try:
            analysis = await self._openai.analyze_transcript(transcription.text)
            logger.info("LLM analysis complete: %s", log_ctx)
        except Exception as exc:
            # LLM failure is non-fatal — save transcript without summary
            logger.warning(
                "LLM analysis failed: %s — %s. Saving transcript only.",
                log_ctx,
                exc,
            )
            await self._repository.update_processing_results(
                memory_id,
                transcript=transcription.text,
                status=MemoryStatus.READY.value,
            )
            return

        # 5. Save all results
        await self._repository.update_processing_results(
            memory_id,
            transcript=transcription.text,
            summary=analysis.summary,
            key_points=analysis.key_points,
            action_items=analysis.action_items,
            title=analysis.title,
            status=MemoryStatus.READY.value,
        )
        logger.info("Processing complete: %s", log_ctx)
