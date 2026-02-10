"""Base exception hierarchy for the RAWK backend.

Each exception carries a status_code so the global exception handler
in main.py can produce consistent HTTP error responses.
"""

from typing import Optional


class RawkException(Exception):
    """Base exception for all RAWK errors."""

    status_code: int = 500
    detail: str = "Internal server error"

    def __init__(self, detail: Optional[str] = None) -> None:
        if detail is not None:
            self.detail = detail
        super().__init__(self.detail)


class ResourceNotFoundError(RawkException):
    """Raised when a requested resource does not exist."""

    status_code = 404
    detail = "Resource not found"


class S3UploadError(RawkException):
    """Raised when an S3 upload or download fails."""

    status_code = 502
    detail = "S3 operation failed"


class SQSPublishError(RawkException):
    """Raised when publishing to SQS fails."""

    status_code = 502
    detail = "SQS publish failed"


class AIProcessingError(RawkException):
    """Raised when an OpenAI API call fails."""

    status_code = 502
    detail = "AI processing failed"


class AIValidationError(RawkException):
    """Raised when AI output fails Pydantic validation after retries."""

    status_code = 422
    detail = "AI output validation failed"


class DatabaseError(RawkException):
    """Raised when a database operation fails."""

    status_code = 500
    detail = "Database operation failed"


class AudioProcessingError(RawkException):
    """Raised when audio processing (transcription, encoding) fails."""

    status_code = 500
    detail = "Audio processing failed"
