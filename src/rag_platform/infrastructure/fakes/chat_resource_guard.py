from uuid import UUID

from rag_platform.application.ports.chat_resources import ChatResourceGuard, ChatSlotLease


class _Lease:
    async def release(self) -> None:
        return None


class NoopChatResourceGuard(ChatResourceGuard):
    async def acquire(self, *, organization_id: UUID) -> ChatSlotLease:
        _ = organization_id
        return _Lease()

    async def reserve_budget(self, *, organization_id: UUID, estimate_usd: float) -> str:
        _ = (organization_id, estimate_usd)
        return "noop"

    async def settle_budget(
        self,
        *,
        organization_id: UUID,
        reservation_id: str,
        actual_usd: float,
    ) -> None:
        _ = (organization_id, reservation_id, actual_usd)

    async def release_budget(self, *, organization_id: UUID, reservation_id: str) -> None:
        _ = (organization_id, reservation_id)
