import json
from datetime import UTC, datetime
from uuid import UUID, uuid4

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from rag_platform.application.ports.api_keys import ApiKeyRecord, ApiKeyRepository
from rag_platform.infrastructure.db.api_key_models import OrganizationApiKeyModel


def _to_record(row: OrganizationApiKeyModel) -> ApiKeyRecord:
    scopes = tuple(json.loads(row.scopes))
    return ApiKeyRecord(
        id=row.id,
        organization_id=row.organization_id,
        name=row.name,
        key_prefix=row.key_prefix,
        key_hash=row.key_hash,
        scopes=scopes,
        created_at=row.created_at,
        expires_at=row.expires_at,
        revoked_at=row.revoked_at,
        last_used_at=row.last_used_at,
    )


class SqlAlchemyApiKeyRepository(ApiKeyRepository):
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create(
        self,
        *,
        organization_id: UUID,
        name: str,
        key_prefix: str,
        key_hash: str,
        scopes: tuple[str, ...],
        expires_at: datetime | None,
    ) -> ApiKeyRecord:
        now = datetime.now(tz=UTC)
        row = OrganizationApiKeyModel(
            id=uuid4(),
            organization_id=organization_id,
            name=name,
            key_prefix=key_prefix,
            key_hash=key_hash,
            scopes=json.dumps(list(scopes)),
            expires_at=expires_at,
            revoked_at=None,
            last_used_at=None,
            created_at=now,
            updated_at=now,
        )
        self._session.add(row)
        await self._session.flush()
        return _to_record(row)

    async def get_by_prefix(self, key_prefix: str) -> ApiKeyRecord | None:
        stmt = select(OrganizationApiKeyModel).where(
            OrganizationApiKeyModel.key_prefix == key_prefix
        )
        row = (await self._session.execute(stmt)).scalar_one_or_none()
        if row is None:
            return None
        return _to_record(row)

    async def list_for_organization(self, organization_id: UUID) -> list[ApiKeyRecord]:
        stmt = select(OrganizationApiKeyModel).where(
            OrganizationApiKeyModel.organization_id == organization_id,
        )
        rows = (await self._session.execute(stmt)).scalars().all()
        return [_to_record(row) for row in rows]

    async def revoke(self, key_id: UUID, revoked_at: datetime) -> None:
        row = await self._session.get(OrganizationApiKeyModel, key_id)
        if row is None:
            return
        row.revoked_at = revoked_at
        row.updated_at = revoked_at
        await self._session.flush()

    async def mark_used(self, key_id: UUID, used_at: datetime) -> None:
        row = await self._session.get(OrganizationApiKeyModel, key_id)
        if row is None:
            return
        row.last_used_at = used_at
        row.updated_at = used_at
        await self._session.flush()
