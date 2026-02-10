"""Async S3 client wrapper. All S3 SDK calls go through this class."""

from __future__ import annotations

import logging
from typing import Optional

import aioboto3

from app.config import Settings
from app.exceptions import S3UploadError

logger = logging.getLogger(__name__)


class S3Client:
    """Async wrapper around S3 operations using aioboto3."""

    def __init__(self, settings: Settings) -> None:
        self._settings = settings
        self._session = aioboto3.Session(
            aws_access_key_id=settings.aws_access_key_id or None,
            aws_secret_access_key=settings.aws_secret_access_key or None,
            region_name=settings.aws_region,
        )

    async def upload_file(
        self,
        file_data: bytes,
        key: str,
        content_type: str = "audio/mpeg",
    ) -> str:
        """Upload file bytes to S3 and return the S3 URL.

        Args:
            file_data: Raw file bytes.
            key: S3 object key (e.g. "audio/<uuid>.webm").
            content_type: MIME type of the file.

        Returns:
            The S3 URL of the uploaded object.

        Raises:
            S3UploadError: If the upload fails.
        """
        bucket = self._settings.s3_bucket_name
        try:
            async with self._session.client("s3") as s3:
                await s3.put_object(
                    Bucket=bucket,
                    Key=key,
                    Body=file_data,
                    ContentType=content_type,
                )
            url = f"s3://{bucket}/{key}"
            logger.info("Uploaded %s (%d bytes)", url, len(file_data))
            return url
        except Exception as exc:
            logger.error("S3 upload failed for key=%s: %s", key, exc)
            raise S3UploadError(detail=f"Failed to upload {key}: {exc}") from exc

    async def get_file(self, key: str) -> bytes:
        """Download a file from S3 and return its bytes.

        Args:
            key: S3 object key.

        Returns:
            The file contents as bytes.

        Raises:
            S3UploadError: If the download fails.
        """
        bucket = self._settings.s3_bucket_name
        try:
            async with self._session.client("s3") as s3:
                response = await s3.get_object(Bucket=bucket, Key=key)
                data = await response["Body"].read()
            logger.info("Downloaded s3://%s/%s (%d bytes)", bucket, key, len(data))
            return data
        except Exception as exc:
            logger.error("S3 download failed for key=%s: %s", key, exc)
            raise S3UploadError(detail=f"Failed to download {key}: {exc}") from exc

    async def generate_presigned_url(
        self,
        key: str,
        expiration: int = 3600,
    ) -> str:
        """Generate a presigned download URL for the given S3 key.

        Args:
            key: S3 object key.
            expiration: URL validity in seconds (default 1 hour).

        Returns:
            A presigned HTTPS URL.

        Raises:
            S3UploadError: If URL generation fails.
        """
        bucket = self._settings.s3_bucket_name
        try:
            async with self._session.client("s3") as s3:
                url = await s3.generate_presigned_url(
                    "get_object",
                    Params={"Bucket": bucket, "Key": key},
                    ExpiresIn=expiration,
                )
            return url
        except Exception as exc:
            logger.error("Presigned URL generation failed for key=%s: %s", key, exc)
            raise S3UploadError(
                detail=f"Failed to generate presigned URL for {key}: {exc}"
            ) from exc
