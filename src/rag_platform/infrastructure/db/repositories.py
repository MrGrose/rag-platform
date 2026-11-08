from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from rag_platform.application.ports.repositories import (
    KnowledgeBaseRepository,
    OrganizationRepository,
)
from rag_platform.domain.entities import KnowledgeBase, Organization
from rag_platform.domain.errors import ConflictError, NotFoundError
from rag_platform.infrastructure.db.models import KnowledgeBaseModel, OrganizationModel


def _to_organization(row: OrganizationModel) -> Organization:
    return Organization(
        id=row.id,
        name=row.name,
        created_at=row.created_at,
        updated_at=row.updated_at,
    )


def _to_knowledge_base(row: KnowledgeBaseModel) -> KnowledgeBase:
    return KnowledgeBase(
        id=row.id,
        organization_id=row.organization_id,
        name=row.name,
        created_at=row.created_at,
        updated_at=row.updated_at,
    )


class SqlAlchemyOrganizationRepository(OrganizationRepository):
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create(self, name: str) -> Organization:
        existing = await self.get_by_name(name)
        if existing is not None:
            raise ConflictError(f"organization already exists: {name}")
        row = OrganizationModel(name=name)
        self._session.add(row)
        await self._session.flush()
        return _to_organization(row)

    async def get_by_id(self, organization_id: UUID) -> Organization | None:
        row = await self._session.get(OrganizationModel, organization_id)
        if row is None:
            return None
        return _to_organization(row)

    async def get_by_name(self, name: str) -> Organization | None:
        stmt = select(OrganizationModel).where(OrganizationModel.name == name)
        result = await self._session.execute(stmt)
        row = result.scalar_one_or_none()
        if row is None:
            return None
        return _to_organization(row)


class SqlAlchemyKnowledgeBaseRepository(KnowledgeBaseRepository):
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create(self, organization_id: UUID, name: str) -> KnowledgeBase:
        org = await self._session.get(OrganizationModel, organization_id)
        if org is None:
            raise NotFoundError(f"organization not found: {organization_id}")
        row = KnowledgeBaseModel(organization_id=organization_id, name=name)
        self._session.add(row)
        await self._session.flush()
        return _to_knowledge_base(row)

    async def get_by_id(self, knowledge_base_id: UUID) -> KnowledgeBase | None:
        row = await self._session.get(KnowledgeBaseModel, knowledge_base_id)
        if row is None:
            return None
        return _to_knowledge_base(row)

    async def list_for_organization(self, organization_id: UUID) -> list[KnowledgeBase]:
        org_col = KnowledgeBaseModel.organization_id
        stmt = select(KnowledgeBaseModel).where(org_col == organization_id)
        result = await self._session.execute(stmt)
        rows = result.scalars().all()
        return [_to_knowledge_base(row) for row in rows]
