"""Pure utility functions for S3 operations. No I/O here."""

from pathlib import Path
from uuid import UUID

CONTENT_TYPE_MAP = {
    ".mp3": "audio/mpeg",
    ".wav": "audio/wav",
    ".webm": "audio/webm",
    ".m4a": "audio/mp4",
    ".ogg": "audio/ogg",
    ".flac": "audio/flac",
    ".aac": "audio/aac",
}


def generate_s3_key(filename: str, memory_id: UUID) -> str:
    """Generate a unique S3 key for an audio file.

    Args:
        filename: Original filename (used to extract extension).
        memory_id: UUID of the memory record.

    Returns:
        S3 key like "audio/<uuid>.webm".
    """
    ext = Path(filename).suffix or ".webm"
    return f"audio/{memory_id}{ext}"


def get_content_type(filename: str) -> str:
    """Determine MIME content type from filename extension.

    Args:
        filename: The filename to inspect.

    Returns:
        MIME type string, defaults to "application/octet-stream".
    """
    ext = Path(filename).suffix.lower()
    return CONTENT_TYPE_MAP.get(ext, "application/octet-stream")
