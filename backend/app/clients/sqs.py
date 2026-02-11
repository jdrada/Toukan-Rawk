"""Async SQS client wrapper. All SQS SDK calls go through this class."""

from __future__ import annotations

import logging
from typing import Dict, List

import aioboto3

from app.config import Settings
from app.exceptions import SQSPublishError
from app.models.memory import MemoryProcessRequest

logger = logging.getLogger(__name__)


class SQSClient:
    """Async wrapper around SQS operations using aioboto3."""

    def __init__(self, settings: Settings) -> None:
        self._settings = settings
        session_kwargs: dict = {"region_name": settings.aws_region}
        if settings.aws_access_key_id:
            session_kwargs["aws_access_key_id"] = settings.aws_access_key_id
        if settings.aws_secret_access_key:
            session_kwargs["aws_secret_access_key"] = settings.aws_secret_access_key
        if settings.aws_session_token:
            session_kwargs["aws_session_token"] = settings.aws_session_token
        self._session = aioboto3.Session(**session_kwargs)

    async def send_message(self, payload: MemoryProcessRequest) -> str:
        """Send a processing job to the SQS queue.

        Args:
            payload: Pydantic model that will be serialized to JSON.

        Returns:
            The SQS MessageId.

        Raises:
            SQSPublishError: If the publish fails.
        """
        queue_url = self._settings.sqs_queue_url
        try:
            async with self._session.client(
                "sqs",
                endpoint_url=self._settings.aws_endpoint_url,
            ) as sqs:
                response = await sqs.send_message(
                    QueueUrl=queue_url,
                    MessageBody=payload.model_dump_json(),
                    MessageAttributes={
                        "correlation_id": {
                            "DataType": "String",
                            "StringValue": payload.correlation_id,
                        },
                    },
                )
            message_id = response["MessageId"]
            logger.info(
                "SQS message sent: message_id=%s, correlation_id=%s",
                message_id,
                payload.correlation_id,
            )
            return message_id
        except Exception as exc:
            logger.error(
                "SQS publish failed for memory_id=%s: %s",
                payload.memory_id,
                exc,
            )
            raise SQSPublishError(
                detail=f"Failed to enqueue processing for memory {payload.memory_id}: {exc}"
            ) from exc

    async def receive_messages(
        self,
        max_messages: int = 1,
        wait_time: int = 20,
    ) -> List[Dict]:
        """Long-poll for messages from the queue.

        Args:
            max_messages: Max number of messages to receive (1-10).
            wait_time: Long-poll wait time in seconds.

        Returns:
            List of SQS message dicts.
        """
        queue_url = self._settings.sqs_queue_url
        try:
            async with self._session.client(
                "sqs",
                endpoint_url=self._settings.aws_endpoint_url,
            ) as sqs:
                response = await sqs.receive_message(
                    QueueUrl=queue_url,
                    MaxNumberOfMessages=max_messages,
                    WaitTimeSeconds=wait_time,
                    MessageAttributeNames=["All"],
                )
            return response.get("Messages", [])
        except Exception as exc:
            logger.error("SQS receive failed: %s", exc)
            return []

    async def delete_message(self, receipt_handle: str) -> None:
        """Delete a message after successful processing.

        Args:
            receipt_handle: The receipt handle from receive_message.
        """
        queue_url = self._settings.sqs_queue_url
        try:
            async with self._session.client(
                "sqs",
                endpoint_url=self._settings.aws_endpoint_url,
            ) as sqs:
                await sqs.delete_message(
                    QueueUrl=queue_url,
                    ReceiptHandle=receipt_handle,
                )
            logger.info("SQS message deleted: receipt_handle=%s...", receipt_handle[:20])
        except Exception as exc:
            logger.error("SQS delete failed: %s", exc)
