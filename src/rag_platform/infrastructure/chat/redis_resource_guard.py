import json
from datetime import UTC, datetime
from uuid import UUID, uuid4

import redis.asyncio as redis

from rag_platform.application.ports.chat_resources import ChatResourceGuard, ChatSlotLease
from rag_platform.config import get_settings
from rag_platform.domain.errors import ConflictError, ServiceUnavailableError
from rag_platform.infrastructure.chat.redis_scripts import (
    ACQUIRE_SLOT_SCRIPT,
    RELEASE_BUDGET_SCRIPT,
    RESERVE_BUDGET_SCRIPT,
    SETTLE_BUDGET_SCRIPT,
)
from rag_platform.infrastructure.metrics import (
    CHAT_BUDGET_EXCEEDED,
    CHAT_CONCURRENCY_REJECTED,
)


class _RedisChatSlotLease:
    def __init__(self, client: redis.Redis, keys: list[str], member: str) -> None:
        self._client = client
        self._keys = keys
        self._member = member
        self._released = False

    async def release(self) -> None:
        if self._released:
            return
        self._released = True
        for key in self._keys:
            await self._client.zrem(key, self._member)


class RedisChatResourceGuard(ChatResourceGuard):
    def __init__(self) -> None:
        settings = get_settings()
        self._client = redis.from_url(str(settings.redis_url), decode_responses=True)
        self._acquire_script = self._client.register_script(ACQUIRE_SLOT_SCRIPT)
        self._reserve_script = self._client.register_script(RESERVE_BUDGET_SCRIPT)
        self._settle_script = self._client.register_script(SETTLE_BUDGET_SCRIPT)
        self._release_script = self._client.register_script(RELEASE_BUDGET_SCRIPT)

    async def acquire(self, *, organization_id: UUID) -> ChatSlotLease:
        settings = get_settings()
        now = datetime.now(tz=UTC).timestamp()
        lease_until = now + settings.chat_concurrency_lease_seconds
        member = uuid4().hex
        global_key = "chat:slots:global"
        org_key = f"chat:slots:org:{organization_id}"
        try:
            ok = await self._acquire_script(
                keys=[global_key, org_key],
                args=[
                    str(now),
                    str(lease_until),
                    member,
                    str(settings.chat_global_concurrency),
                    str(settings.chat_org_concurrency),
                ],
            )
            code = int(ok)
            if code != 1:
                scope = "global" if code == 2 else "organization"
                CHAT_CONCURRENCY_REJECTED.labels(scope=scope).inc()
                raise ConflictError("chat concurrency limit exceeded")
        except ConflictError:
            raise
        except (
            ConnectionError,
            OSError,
            TimeoutError,
            redis.ConnectionError,
            redis.TimeoutError,
        ) as exc:
            if settings.rate_limit_fail_closed:
                raise ServiceUnavailableError("chat resource guard unavailable") from exc
            return _NoopLease()
        return _RedisChatSlotLease(self._client, [global_key, org_key], member)

    async def reserve_budget(self, *, organization_id: UUID, estimate_usd: float) -> str:
        settings = get_settings()
        if estimate_usd > settings.chat_max_request_cost_usd:
            CHAT_BUDGET_EXCEEDED.labels(reason="per_request").inc()
            raise ConflictError("chat request cost limit exceeded")
        day = datetime.now(tz=UTC).strftime("%Y%m%d")
        key = f"chat:budget:org:{organization_id}:{day}"
        reservation_id = uuid4().hex
        res_key = f"chat:budget:reservation:{reservation_id}"
        payload = json.dumps({"org": str(organization_id), "amount": estimate_usd})
        try:
            ok = await self._reserve_script(
                keys=[key],
                args=[
                    str(estimate_usd),
                    str(settings.chat_daily_org_budget_usd),
                    res_key,
                    payload,
                    "3600",
                    "172800",
                ],
            )
        except (
            ConnectionError,
            OSError,
            TimeoutError,
            redis.ConnectionError,
            redis.TimeoutError,
        ) as exc:
            if settings.rate_limit_fail_closed:
                raise ServiceUnavailableError("chat resource guard unavailable") from exc
            return reservation_id
        if int(ok) != 1:
            CHAT_BUDGET_EXCEEDED.labels(reason="daily").inc()
            raise ConflictError("organization daily chat budget exceeded")
        return reservation_id

    async def settle_budget(
        self,
        *,
        organization_id: UUID,
        reservation_id: str,
        actual_usd: float,
    ) -> None:
        day = datetime.now(tz=UTC).strftime("%Y%m%d")
        budget_key = f"chat:budget:org:{organization_id}:{day}"
        res_key = f"chat:budget:reservation:{reservation_id}"
        raw = await self._client.get(res_key)
        reserved = 0.0
        if raw:
            reserved = float(json.loads(raw)["amount"])
        await self._settle_script(
            keys=[budget_key, res_key],
            args=[str(actual_usd), str(reserved)],
        )

    async def release_budget(self, *, organization_id: UUID, reservation_id: str) -> None:
        day = datetime.now(tz=UTC).strftime("%Y%m%d")
        budget_key = f"chat:budget:org:{organization_id}:{day}"
        res_key = f"chat:budget:reservation:{reservation_id}"
        raw = await self._client.get(res_key)
        amount = 0.0
        if raw:
            amount = float(json.loads(raw)["amount"])
        await self._release_script(keys=[budget_key, res_key], args=[str(amount)])


class _NoopLease:
    async def release(self) -> None:
        return None
