from typing import Protocol
from uuid import UUID


class ChatSlotLease(Protocol):
    async def release(self) -> None: ...


class ChatResourceGuard(Protocol):
    async def acquire(self, *, organization_id: UUID) -> ChatSlotLease: ...

    async def reserve_budget(self, *, organization_id: UUID, estimate_usd: float) -> str: ...

    async def settle_budget(
        self,
        *,
        organization_id: UUID,
        reservation_id: str,
        actual_usd: float,
    ) -> None: ...

    async def release_budget(
        self,
        *,
        organization_id: UUID,
        reservation_id: str,
    ) -> None: ...
