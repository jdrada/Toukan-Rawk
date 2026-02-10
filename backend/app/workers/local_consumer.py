"""Local development SQS consumer.

Long-polls the SQS queue and processes messages without Lambda.
Run with: python -m app.workers.local_consumer
"""

from __future__ import annotations

import asyncio
import json
import logging
import sys

from app.clients.openai import OpenAIClient
from app.clients.s3 import S3Client
from app.clients.sqs import SQSClient
from app.config import Settings
from app.models.memory import MemoryProcessRequest
from app.repositories.database import _get_session_factory, _get_engine
from app.repositories.memory_repository import MemoryRepository
from app.services.processing_service import ProcessingService

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)


async def consume_forever(settings: Settings) -> None:
    """Long-poll the SQS queue and process messages."""
    sqs = SQSClient(settings)
    s3_client = S3Client(settings)
    openai_client = OpenAIClient(settings)

    engine = _get_engine(settings)
    factory = _get_session_factory(settings)

    logger.info("Local consumer started. Polling %s", settings.sqs_queue_url)

    while True:
        messages = await sqs.receive_messages(max_messages=1, wait_time=20)

        for msg in messages:
            receipt_handle = msg["ReceiptHandle"]
            try:
                body = json.loads(msg["Body"])
                payload = MemoryProcessRequest.model_validate(body)

                logger.info(
                    "Processing: memory_id=%s, correlation_id=%s",
                    payload.memory_id,
                    payload.correlation_id,
                )

                async with factory() as session:
                    repository = MemoryRepository(session)
                    service = ProcessingService(
                        repository, s3_client, openai_client
                    )
                    await service.process_memory(
                        memory_id=payload.memory_id,
                        audio_url=payload.audio_url,
                        correlation_id=payload.correlation_id,
                    )
                    await session.commit()

                await sqs.delete_message(receipt_handle)
                logger.info("Processed and deleted: memory_id=%s", payload.memory_id)

            except Exception as exc:
                logger.error(
                    "Failed to process message: %s",
                    exc,
                    exc_info=True,
                )
                # Message returns to queue after visibility timeout


if __name__ == "__main__":
    settings = Settings()
    if not settings.sqs_queue_url:
        logger.error("SQS_QUEUE_URL not set. Cannot start consumer.")
        sys.exit(1)
    asyncio.run(consume_forever(settings))
