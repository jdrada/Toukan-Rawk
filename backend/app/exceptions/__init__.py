"""Custom exception classes for RAWK backend."""

from app.exceptions.base import (
    AIProcessingError,
    AIValidationError,
    AudioProcessingError,
    DatabaseError,
    RawkException,
    ResourceNotFoundError,
    S3UploadError,
    SQSPublishError,
)

__all__ = [
    "RawkException",
    "ResourceNotFoundError",
    "S3UploadError",
    "SQSPublishError",
    "AIProcessingError",
    "AIValidationError",
    "DatabaseError",
    "AudioProcessingError",
]
