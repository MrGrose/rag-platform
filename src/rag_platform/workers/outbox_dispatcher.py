from datetime import UTC, datetime, timedelta
from uuid import UUID, uuid4

from rag_platform.application.ports.outbox import OutboxRepository
from rag_platform.config import get_settings
from rag_platform.infrastructure.db.outbox_repository import SqlAlchemyOutboxRepository
from rag_platform.infrastructure.db.session import session_scope
from rag_platform.infrastructure.queue.arq import REDIS_QUEUE_ERRORS, enqueue_run_evaluation


def _backoff_seconds(attempts: int, settings) -> int:
    return min(
        settings.outbox_base_backoff_seconds * (2 ** max(attempts - 1, 0)),
        3600,
    )


async def dispatch_outbox_events(_ctx: dict) -> str:
    settings = get_settings()
    lock_token = uuid4().hex
    now = datetime.now(tz=UTC)
    claimed: list = []

    async with session_scope() as session:
        repo: OutboxRepository = SqlAlchemyOutboxRepository(session)
        await repo.release_stale_processing(
            now=now,
            lease_seconds=settings.outbox_lease_seconds,
        )
        claimed = await repo.claim_batch(
            limit=settings.outbox_batch_size,
            lock_token=lock_token,
            locked_at=now,
            now=now,
        )
        await session.commit()

    published = 0
    for event in claimed:
        try:
            if event.event_type == "evaluation.run":
                payload = event.payload
                await enqueue_run_evaluation(
                    UUID(payload["evaluation_id"]),
                    UUID(payload["knowledge_base_id"]),
                    UUID(payload["organization_id"]),
                )
            else:
                raise ValueError(f"unsupported outbox event: {event.event_type}")
        except REDIS_QUEUE_ERRORS as exc:
            attempts = event.attempts + 1
            async with session_scope() as session:
                repo = SqlAlchemyOutboxRepository(session)
                if attempts >= settings.outbox_max_attempts:
                    await repo.mark_dead(event.id, last_error=str(exc))
                else:
                    await repo.mark_retry(
                        event.id,
                        attempts=attempts,
                        available_at=now + timedelta(seconds=_backoff_seconds(attempts, settings)),
                        last_error=str(exc),
                    )
                await session.commit()
            continue
        except Exception as exc:
            attempts = event.attempts + 1
            async with session_scope() as session:
                repo = SqlAlchemyOutboxRepository(session)
                if attempts >= settings.outbox_max_attempts:
                    await repo.mark_dead(event.id, last_error=str(exc))
                else:
                    await repo.mark_retry(
                        event.id,
                        attempts=attempts,
                        available_at=now + timedelta(seconds=_backoff_seconds(attempts, settings)),
                        last_error=str(exc),
                    )
                await session.commit()
            continue

        async with session_scope() as session:
            repo = SqlAlchemyOutboxRepository(session)
            await repo.mark_published(event.id, datetime.now(tz=UTC))
            await session.commit()
        published += 1

    return str(published)
