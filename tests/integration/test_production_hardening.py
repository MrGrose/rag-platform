import os
import uuid

import pytest
import redis.asyncio as redis_async

pytestmark = pytest.mark.integration


@pytest.fixture
async def redis_client():
    url = os.environ.get("REDIS_URL", "redis://localhost:6380/0")
    client = redis_async.from_url(url, decode_responses=True)
    try:
        await client.ping()
    except (ConnectionError, OSError, TimeoutError) as exc:
        pytest.skip(f"redis unavailable: {exc}")
    yield client
    await client.aclose()


@pytest.mark.asyncio
async def test_chat_guard_concurrent_acquire(
    redis_client,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from rag_platform.config.settings import get_settings
    from rag_platform.domain.errors import ConflictError
    from rag_platform.infrastructure.chat.redis_resource_guard import RedisChatResourceGuard

    _ = redis_client
    monkeypatch.setenv("REDIS_URL", os.environ.get("REDIS_URL", "redis://localhost:6380/0"))
    monkeypatch.setenv("CHAT_GLOBAL_CONCURRENCY", "1")
    monkeypatch.setenv("CHAT_ORG_CONCURRENCY", "1")
    monkeypatch.setenv("RATE_LIMIT_FAIL_CLOSED", "true")
    get_settings.cache_clear()
    org = uuid.uuid4()
    guard = RedisChatResourceGuard()
    lease1 = await guard.acquire(organization_id=org)
    with pytest.raises(ConflictError):
        await guard.acquire(organization_id=org)
    await lease1.release()
    lease2 = await guard.acquire(organization_id=org)
    await lease2.release()
    get_settings.cache_clear()


@pytest.mark.asyncio
async def test_chat_budget_concurrent_reserve(
    redis_client,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from rag_platform.config.settings import get_settings
    from rag_platform.domain.errors import ConflictError
    from rag_platform.infrastructure.chat.redis_resource_guard import RedisChatResourceGuard

    _ = redis_client
    monkeypatch.setenv("REDIS_URL", os.environ.get("REDIS_URL", "redis://localhost:6380/0"))
    monkeypatch.setenv("CHAT_DAILY_ORG_BUDGET_USD", "0.05")
    monkeypatch.setenv("CHAT_MAX_REQUEST_COST_USD", "0.03")
    monkeypatch.setenv("RATE_LIMIT_FAIL_CLOSED", "true")
    get_settings.cache_clear()
    org = uuid.uuid4()
    guard = RedisChatResourceGuard()
    await guard.reserve_budget(organization_id=org, estimate_usd=0.03)
    with pytest.raises(ConflictError):
        await guard.reserve_budget(organization_id=org, estimate_usd=0.03)
    get_settings.cache_clear()
