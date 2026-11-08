from datetime import UTC, datetime

from rag_platform.application.ports.api_keys import ApiKeyRepository
from rag_platform.application.security.api_key_hash import parse_key_prefix, verify_api_key
from rag_platform.domain.errors import ValidationError
from rag_platform.domain.tenant import TenantContext


class TenantApiKeyAuthentication:
    def __init__(self, *, api_keys: ApiKeyRepository, pepper: str) -> None:
        self._api_keys = api_keys
        self._pepper = pepper

    async def authenticate(self, raw_key: str) -> TenantContext | None:
        prefix = parse_key_prefix(raw_key)
        if prefix is None:
            return None
        record = await self._api_keys.get_by_prefix(prefix)
        if record is None:
            return None
        if record.revoked_at is not None:
            return None
        now = datetime.now(tz=UTC)
        if record.expires_at is not None and record.expires_at <= now:
            return None
        if not verify_api_key(raw_key, self._pepper, record.key_hash):
            return None
        await self._api_keys.mark_used(record.id, now)
        return TenantContext(
            organization_id=record.organization_id,
            api_key_id=record.id,
            scopes=record.scopes,
            auth_mode="api_key",
        )

    async def authenticate_or_raise(self, raw_key: str) -> TenantContext:
        tenant = await self.authenticate(raw_key)
        if tenant is None:
            raise ValidationError("unauthorized")
        return tenant
