"""Pydantic models for validating AI (OpenAI) outputs."""

from typing import List, Optional

from pydantic import BaseModel, Field, field_validator


class TranscriptionResult(BaseModel):
    """Validated Whisper transcription output."""

    text: str
    language: Optional[str] = None
    duration: Optional[float] = None


class LLMAnalysisResult(BaseModel):
    """Strict schema for LLM summary and extraction output.

    The LLM is prompted to return JSON matching this schema.
    Validation failures trigger retries with exponential backoff.
    """

    title: str = Field(..., min_length=1, max_length=200)
    summary: str = Field(..., min_length=10)
    key_points: List[str] = Field(..., min_length=1, max_length=10)
    action_items: List[str] = Field(default_factory=list)

    @field_validator("key_points")
    @classmethod
    def validate_key_points_not_empty(cls, v: List[str]) -> List[str]:
        if not v:
            raise ValueError("At least one key point is required")
        return v


class LLMAnalysisFallback(BaseModel):
    """Fallback values used when LLM output fails validation after all retries."""

    title: str = "Untitled Memory"
    summary: str = "Summary could not be generated. Please review the transcript."
    key_points: List[str] = Field(
        default=["Processing failed - review transcript manually"]
    )
    action_items: List[str] = Field(default_factory=list)
