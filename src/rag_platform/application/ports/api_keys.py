from datetime import datetime
from typing import Protocol
from uuid import UUID


class ApiKeyRecord:
    def __init__(
        self,
        *,
        id: UUID,
        organization_id: UUID,
        name: str,
        key_prefix: str,
        key_hash: str,
        scopes: tuple[str, ...],
        created_at: datetime,
        expires_at: datetime | None,
        revoked_at: datetime | None,
        last_used_at: datetime | None,
    ) -> None:
        self.id = id
        self.organization_id = organization_id
        self.name = name
        self.key_prefix = key_prefix
        self.key_hash = key_hash
        self.scopes = scopes
        self.created_at = created_at
        self.expires_at = expires_at
        self.revoked_at = revoked_at
        self.last_used_at = last_used_at


class ApiKeyRepository(Protocol):
    async def create(
        self,
        *,
        organization_id: UUID,
        name: str,
        key_prefix: str,
        key_hash: str,
        scopes: tuple[str, ...],
        expires_at: datetime | None,
    ) -> ApiKeyRecord: ...

    async def get_by_prefix(self, key_prefix: str) -> ApiKeyRecord | None: ...

    async def list_for_organization(self, organization_id: UUID) -> list[ApiKeyRecord]: ...

    async def revoke(self, key_id: UUID, revoked_at: datetime) -> None: ...

    async def mark_used(self, key_id: UUID, used_at: datetime) -> None: ...
