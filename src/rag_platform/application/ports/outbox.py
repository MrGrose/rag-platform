from datetime import datetime
from typing import Any, Protocol
from uuid import UUID


class OutboxEvent:
    def __init__(
        self,
        *,
        id: UUID,
        event_type: str,
        aggregate_id: UUID,
        organization_id: UUID,
        payload: dict[str, Any],
        status: str,
        attempts: int,
        available_at: datetime,
        created_at: datetime,
        published_at: datetime | None,
        last_error: str | None,
        lock_token: str | None,
        locked_at: datetime | None,
    ) -> None:
        self.id = id
        self.event_type = event_type
        self.aggregate_id = aggregate_id
        self.organization_id = organization_id
        self.payload = payload
        self.status = status
        self.attempts = attempts
        self.available_at = available_at
        self.created_at = created_at
        self.published_at = published_at
        self.last_error = last_error
        self.lock_token = lock_token
        self.locked_at = locked_at


class OutboxRepository(Protocol):
    async def append(
        self,
        *,
        event_type: str,
        aggregate_id: UUID,
        organization_id: UUID,
        payload: dict[str, Any],
    ) -> UUID: ...

    async def claim_batch(
        self,
        *,
        limit: int,
        lock_token: str,
        locked_at: datetime,
        now: datetime,
    ) -> list[OutboxEvent]: ...

    async def mark_published(self, event_id: UUID, published_at: datetime) -> None: ...

    async def mark_retry(
        self,
        event_id: UUID,
        *,
        attempts: int,
        available_at: datetime,
        last_error: str,
    ) -> None: ...

    async def mark_dead(self, event_id: UUID, *, last_error: str) -> None: ...

    async def release_stale_processing(
        self,
        *,
        now,
        lease_seconds: int,
    ) -> int: ...
