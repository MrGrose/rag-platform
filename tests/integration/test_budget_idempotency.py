import asyncio
import os
import uuid

import pytest

pytestmark = pytest.mark.integration


@pytest.mark.asyncio
async def test_budget_settle_release_idempotent(monkeypatch: pytest.MonkeyPatch) -> None:
    from rag_platform.config.settings import get_settings
    from rag_platform.infrastructure.chat.redis_resource_guard import RedisChatResourceGuard

    monkeypatch.setenv("REDIS_URL", os.environ.get("REDIS_URL", "redis://localhost:6380/0"))
    monkeypatch.setenv("CHAT_DAILY_ORG_BUDGET_USD", "10")
    monkeypatch.setenv("CHAT_MAX_REQUEST_COST_USD", "1")
    monkeypatch.setenv("RATE_LIMIT_FAIL_CLOSED", "true")
    get_settings.cache_clear()
    org = uuid.uuid4()
    guard = RedisChatResourceGuard()
    reservation = await guard.reserve_budget(organization_id=org, estimate_usd=0.5)
    await guard.settle_budget(organization_id=org, reservation_id=reservation, actual_usd=0.5)
    await guard.settle_budget(organization_id=org, reservation_id=reservation, actual_usd=0.9)
    await guard.release_budget(organization_id=org, reservation_id=reservation)


@pytest.mark.asyncio
async def test_budget_concurrent_settle_single_effect(monkeypatch: pytest.MonkeyPatch) -> None:
    from rag_platform.config.settings import get_settings
    from rag_platform.infrastructure.chat.redis_resource_guard import RedisChatResourceGuard

    monkeypatch.setenv("REDIS_URL", os.environ.get("REDIS_URL", "redis://localhost:6380/0"))
    monkeypatch.setenv("CHAT_DAILY_ORG_BUDGET_USD", "10")
    monkeypatch.setenv("CHAT_MAX_REQUEST_COST_USD", "1")
    monkeypatch.setenv("RATE_LIMIT_FAIL_CLOSED", "true")
    get_settings.cache_clear()
    org = uuid.uuid4()
    guard = RedisChatResourceGuard()
    reservation = await guard.reserve_budget(organization_id=org, estimate_usd=0.5)

    async def settle():
        await guard.settle_budget(
            organization_id=org,
            reservation_id=reservation,
            actual_usd=0.2,
        )

    await asyncio.gather(settle(), settle(), settle())
    await guard.release_budget(organization_id=org, reservation_id=reservation)
