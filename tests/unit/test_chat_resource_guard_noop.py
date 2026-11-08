from uuid import uuid4

import pytest

from rag_platform.infrastructure.fakes.chat_resource_guard import NoopChatResourceGuard


@pytest.mark.asyncio
async def test_noop_guard_acquire_release() -> None:
    guard = NoopChatResourceGuard()
    lease = await guard.acquire(organization_id=uuid4())
    reservation = await guard.reserve_budget(organization_id=uuid4(), estimate_usd=0.01)
    await guard.settle_budget(organization_id=uuid4(), reservation_id=reservation, actual_usd=0.0)
    await lease.release()
