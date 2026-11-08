from uuid import UUID

import redis.asyncio as redis
from arq import create_pool
from arq.connections import RedisSettings

from rag_platform.config import get_settings


async def _enqueue(job_name: str, *args: str) -> None:
    pool = await create_pool(RedisSettings.from_dsn(str(get_settings().arq_redis_url)))
    try:
        await pool.enqueue_job(job_name, *args)
    finally:
        await pool.aclose()


async def enqueue_process_document(
    document_id: UUID,
    knowledge_base_id: UUID,
    organization_id: UUID,
) -> None:
    await _enqueue(
        "process_document",
        str(document_id),
        str(knowledge_base_id),
        str(organization_id),
    )


async def enqueue_delete_document_vectors(
    document_id: UUID,
    knowledge_base_id: UUID,
    organization_id: UUID,
) -> None:
    await _enqueue(
        "delete_document_vectors",
        str(document_id),
        str(knowledge_base_id),
        str(organization_id),
    )


async def enqueue_run_evaluation(
    evaluation_id: UUID,
    knowledge_base_id: UUID,
    organization_id: UUID,
) -> None:
    await _enqueue(
        "run_evaluation",
        str(evaluation_id),
        str(knowledge_base_id),
        str(organization_id),
    )


REDIS_QUEUE_ERRORS: tuple[type[BaseException], ...] = (
    ConnectionError,
    OSError,
    TimeoutError,
    redis.ConnectionError,
    redis.TimeoutError,
)
