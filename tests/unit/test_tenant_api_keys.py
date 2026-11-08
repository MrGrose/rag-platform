from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest

from rag_platform.application.auth.resolve_tenant_api_key import TenantApiKeyAuthentication
from rag_platform.application.ports.api_keys import ApiKeyRecord
from rag_platform.application.security.api_key_hash import generate_api_key, hash_api_key


class _MemoryApiKeys:
    def __init__(self) -> None:
        self.by_prefix: dict[str, ApiKeyRecord] = {}

    async def get_by_prefix(self, prefix: str) -> ApiKeyRecord | None:
        return self.by_prefix.get(prefix)

    async def mark_used(self, key_id, used_at) -> None:
        return None


def _record(org, prefix, full, pepper, *, revoked_at=None, expires_at=None) -> ApiKeyRecord:
    now = datetime.now(tz=UTC)
    return ApiKeyRecord(
        id=uuid4(),
        organization_id=org,
        name="k",
        key_prefix=prefix,
        key_hash=hash_api_key(full, pepper),
        scopes=("*",),
        created_at=now,
        expires_at=expires_at,
        revoked_at=revoked_at,
        last_used_at=None,
    )


@pytest.mark.asyncio
async def test_valid_key_resolves_tenant() -> None:
    org = uuid4()
    pepper = "unit-test-pepper"
    prefix, full = generate_api_key()
    repo = _MemoryApiKeys()
    key_id = uuid4()
    rec = _record(org, prefix, full, pepper)
    rec.id = key_id
    repo.by_prefix[prefix] = rec
    auth = TenantApiKeyAuthentication(api_keys=repo, pepper=pepper)
    tenant = await auth.authenticate(full)
    assert tenant is not None
    assert tenant.organization_id == org
    assert tenant.api_key_id == key_id


@pytest.mark.asyncio
async def test_unknown_key_returns_none() -> None:
    auth = TenantApiKeyAuthentication(api_keys=_MemoryApiKeys(), pepper="pepper")
    assert await auth.authenticate("rk_bad_badsecret") is None


@pytest.mark.asyncio
async def test_revoked_key_returns_none() -> None:
    org = uuid4()
    pepper = "pepper"
    prefix, full = generate_api_key()
    repo = _MemoryApiKeys()
    repo.by_prefix[prefix] = _record(
        org,
        prefix,
        full,
        pepper,
        revoked_at=datetime.now(tz=UTC),
    )
    auth = TenantApiKeyAuthentication(api_keys=repo, pepper=pepper)
    assert await auth.authenticate(full) is None


@pytest.mark.asyncio
async def test_expired_key_returns_none() -> None:
    org = uuid4()
    pepper = "pepper"
    prefix, full = generate_api_key()
    repo = _MemoryApiKeys()
    repo.by_prefix[prefix] = _record(
        org,
        prefix,
        full,
        pepper,
        expires_at=datetime.now(tz=UTC) - timedelta(hours=1),
    )
    auth = TenantApiKeyAuthentication(api_keys=repo, pepper=pepper)
    assert await auth.authenticate(full) is None


def test_hash_does_not_store_plaintext() -> None:
    _, full = generate_api_key()
    hashed = hash_api_key(full, "pepper")
    assert full not in hashed
    assert hashed != full
