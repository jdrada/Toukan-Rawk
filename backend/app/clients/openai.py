"""Async OpenAI client wrapper. All OpenAI API calls go through this class."""

from __future__ import annotations

import asyncio
import io
import logging
from typing import Optional

from openai import AsyncOpenAI

from app.config import Settings
from app.exceptions import AIProcessingError, AIValidationError
from app.models.ai import (
    LLMAnalysisFallback,
    LLMAnalysisResult,
    TranscriptionResult,
)
from app.utils.prompts import build_analysis_prompt

logger = logging.getLogger(__name__)


class OpenAIClient:
    """Async wrapper around OpenAI API for transcription and analysis."""

    def __init__(self, settings: Settings) -> None:
        self._client = AsyncOpenAI(api_key=settings.openai_api_key)
        self._model = settings.openai_model
        self._whisper_model = settings.whisper_model

    async def transcribe_audio(
        self,
        audio_data: bytes,
        filename: str = "audio.webm",
    ) -> TranscriptionResult:
        """Transcribe audio using Whisper.

        Args:
            audio_data: Raw audio file bytes.
            filename: Filename hint for the API (helps with format detection).

        Returns:
            Validated TranscriptionResult.

        Raises:
            AIProcessingError: If the Whisper API call fails.
        """
        try:
            audio_file = io.BytesIO(audio_data)
            audio_file.name = filename

            response = await self._client.audio.transcriptions.create(
                model=self._whisper_model,
                file=audio_file,
                response_format="verbose_json",
            )

            return TranscriptionResult(
                text=response.text,
                language=getattr(response, "language", None),
                duration=getattr(response, "duration", None),
            )
        except Exception as exc:
            logger.error("Whisper transcription failed: %s", exc)
            raise AIProcessingError(
                detail=f"Transcription failed: {exc}"
            ) from exc

    async def analyze_transcript(
        self,
        transcript: str,
        max_retries: int = 3,
    ) -> LLMAnalysisResult:
        """Analyze a transcript with GPT-4 to extract summary, key points, and actions.

        Retries with exponential backoff on parse failures.
        Returns LLMAnalysisFallback values if all retries fail.

        Args:
            transcript: The full transcript text.
            max_retries: Number of attempts before falling back.

        Returns:
            Validated LLMAnalysisResult (or fallback values).
        """
        system_prompt, user_prompt = build_analysis_prompt(transcript)
        last_error: Optional[Exception] = None

        for attempt in range(max_retries):
            try:
                response = await self._client.chat.completions.create(
                    model=self._model,
                    messages=[
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_prompt},
                    ],
                    temperature=0.3,
                    response_format={"type": "json_object"},
                )

                raw_content = response.choices[0].message.content
                if raw_content is None:
                    raise AIValidationError(detail="LLM returned empty content")

                result = LLMAnalysisResult.model_validate_json(raw_content)
                logger.info("LLM analysis succeeded on attempt %d", attempt + 1)
                return result

            except AIValidationError:
                raise
            except Exception as exc:
                last_error = exc
                logger.warning(
                    "LLM analysis attempt %d/%d failed: %s",
                    attempt + 1,
                    max_retries,
                    exc,
                )
                if attempt < max_retries - 1:
                    delay = 2 ** attempt
                    await asyncio.sleep(delay)

        # All retries exhausted — return fallback
        logger.error(
            "LLM analysis failed after %d attempts. Last error: %s",
            max_retries,
            last_error,
        )
        fallback = LLMAnalysisFallback()
        return LLMAnalysisResult(
            title=fallback.title,
            summary=fallback.summary,
            key_points=fallback.key_points,
            action_items=fallback.action_items,
        )
