from datetime import UTC, datetime, timedelta
from typing import Any
from uuid import UUID, uuid4

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from rag_platform.application.ports.outbox import OutboxEvent, OutboxRepository
from rag_platform.infrastructure.db.outbox_models import OutboxEventModel


def _to_event(row: OutboxEventModel) -> OutboxEvent:
    return OutboxEvent(
        id=row.id,
        event_type=row.event_type,
        aggregate_id=row.aggregate_id,
        organization_id=row.organization_id,
        payload=dict(row.payload),
        status=row.status,
        attempts=row.attempts,
        available_at=row.available_at,
        created_at=row.created_at,
        published_at=row.published_at,
        last_error=row.last_error,
        lock_token=row.lock_token,
        locked_at=row.locked_at,
    )


class SqlAlchemyOutboxRepository(OutboxRepository):
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def append(
        self,
        *,
        event_type: str,
        aggregate_id: UUID,
        organization_id: UUID,
        payload: dict[str, Any],
    ) -> UUID:
        now = datetime.now(tz=UTC)
        event_id = uuid4()
        self._session.add(
            OutboxEventModel(
                id=event_id,
                event_type=event_type,
                aggregate_id=aggregate_id,
                organization_id=organization_id,
                payload=payload,
                status="pending",
                attempts=0,
                available_at=now,
                published_at=None,
                last_error=None,
                lock_token=None,
                locked_at=None,
                created_at=now,
                updated_at=now,
            ),
        )
        await self._session.flush()
        return event_id

    async def claim_batch(
        self,
        *,
        limit: int,
        lock_token: str,
        locked_at: datetime,
        now: datetime,
    ) -> list[OutboxEvent]:
        stmt = (
            select(OutboxEventModel)
            .where(
                OutboxEventModel.status == "pending",
                OutboxEventModel.available_at <= now,
            )
            .order_by(OutboxEventModel.created_at)
            .limit(limit)
            .with_for_update(skip_locked=True)
        )
        rows = list((await self._session.execute(stmt)).scalars().all())
        for row in rows:
            row.status = "processing"
            row.lock_token = lock_token
            row.locked_at = locked_at
            row.updated_at = locked_at
        if rows:
            await self._session.flush()
        return [_to_event(row) for row in rows]

    async def mark_published(self, event_id: UUID, published_at: datetime) -> None:
        await self._session.execute(
            update(OutboxEventModel)
            .where(OutboxEventModel.id == event_id)
            .values(
                status="published",
                published_at=published_at,
                lock_token=None,
                locked_at=None,
                updated_at=published_at,
            ),
        )

    async def mark_retry(
        self,
        event_id: UUID,
        *,
        attempts: int,
        available_at: datetime,
        last_error: str,
    ) -> None:
        await self._session.execute(
            update(OutboxEventModel)
            .where(OutboxEventModel.id == event_id)
            .values(
                status="pending",
                attempts=attempts,
                available_at=available_at,
                last_error=last_error,
                lock_token=None,
                locked_at=None,
                updated_at=datetime.now(tz=UTC),
            ),
        )

    async def release_stale_processing(self, *, now: datetime, lease_seconds: int) -> int:
        cutoff = now - timedelta(seconds=lease_seconds)
        result = await self._session.execute(
            update(OutboxEventModel)
            .where(OutboxEventModel.status == "processing")
            .where(OutboxEventModel.locked_at.is_not(None))
            .where(OutboxEventModel.locked_at < cutoff)
            .values(
                status="pending",
                lock_token=None,
                locked_at=None,
                updated_at=now,
            )
        )
        return int(result.rowcount or 0)

    async def mark_dead(self, event_id: UUID, *, last_error: str) -> None:
        await self._session.execute(
            update(OutboxEventModel)
            .where(OutboxEventModel.id == event_id)
            .values(
                status="dead",
                last_error=last_error,
                lock_token=None,
                locked_at=None,
                updated_at=datetime.now(tz=UTC),
            ),
        )
