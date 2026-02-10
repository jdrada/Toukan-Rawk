"""AWS Lambda handler for SQS-triggered memory processing.

This module is the entry point for Lambda functions that consume
SQS messages and run the audio processing pipeline.
"""

from __future__ import annotations

import asyncio
import json
import logging
from typing import Any, Dict, List
from uuid import UUID

from app.clients.openai import OpenAIClient
from app.clients.s3 import S3Client
from app.config import Settings
from app.models.memory import MemoryProcessRequest
from app.repositories.database import _get_session_factory, _get_engine
from app.repositories.memory_repository import MemoryRepository
from app.services.processing_service import ProcessingService

logger = logging.getLogger(__name__)


async def _process_record(record: Dict[str, Any]) -> None:
    """Process a single SQS record through the full pipeline.

    Parses the message body, creates dependencies, and runs processing.
    """
    body = json.loads(record["body"])
    payload = MemoryProcessRequest.model_validate(body)

    logger.info(
        "Processing SQS record: memory_id=%s, correlation_id=%s",
        payload.memory_id,
        payload.correlation_id,
    )

    settings = Settings()
    s3_client = S3Client(settings)
    openai_client = OpenAIClient(settings)

    engine = _get_engine(settings)
    factory = _get_session_factory(settings)

    async with factory() as session:
        repository = MemoryRepository(session)
        service = ProcessingService(repository, s3_client, openai_client)

        await service.process_memory(
            memory_id=payload.memory_id,
            audio_url=payload.audio_url,
            correlation_id=payload.correlation_id,
        )
        await session.commit()


def handler(event: Dict[str, Any], context: Any) -> Dict[str, List]:
    """AWS Lambda entry point for SQS events.

    Processes each SQS record independently. Returns partial batch
    failures so only failed messages are retried.

    Args:
        event: SQS event with "Records" list.
        context: Lambda context (unused).

    Returns:
        Dict with "batchItemFailures" for failed records.
    """
    loop = asyncio.new_event_loop()
    failures: List[Dict[str, str]] = []

    for record in event.get("Records", []):
        try:
            loop.run_until_complete(_process_record(record))
        except Exception as exc:
            message_id = record.get("messageId", "unknown")
            logger.error(
                "Failed to process SQS record %s: %s",
                message_id,
                exc,
                exc_info=True,
            )
            failures.append({"itemIdentifier": message_id})

    loop.close()

    if failures:
        logger.warning("Batch had %d failures out of %d records",
                       len(failures), len(event.get("Records", [])))

    return {"batchItemFailures": failures}
