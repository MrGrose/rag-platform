from datetime import UTC, datetime
from uuid import UUID, uuid4

from rag_platform.application.ports.repositories import (
    KnowledgeBaseRepository,
    OrganizationRepository,
)
from rag_platform.domain.entities import KnowledgeBase, Organization
from rag_platform.domain.errors import ConflictError, NotFoundError


class InMemoryOrganizationRepository(OrganizationRepository):
    def __init__(self) -> None:
        self._by_id: dict[UUID, Organization] = {}
        self._by_name: dict[str, Organization] = {}

    async def create(self, name: str) -> Organization:
        if name in self._by_name:
            raise ConflictError(f"organization already exists: {name}")
        now = datetime.now(tz=UTC)
        org = Organization(id=uuid4(), name=name, created_at=now, updated_at=now)
        self._by_id[org.id] = org
        self._by_name[name] = org
        return org

    async def get_by_id(self, organization_id: UUID) -> Organization | None:
        return self._by_id.get(organization_id)

    async def get_by_name(self, name: str) -> Organization | None:
        return self._by_name.get(name)


class InMemoryKnowledgeBaseRepository(KnowledgeBaseRepository):
    def __init__(self, organizations: InMemoryOrganizationRepository) -> None:
        self._organizations = organizations
        self._by_id: dict[UUID, KnowledgeBase] = {}
        self._by_org: dict[UUID, list[KnowledgeBase]] = {}

    async def create(self, organization_id: UUID, name: str) -> KnowledgeBase:
        if await self._organizations.get_by_id(organization_id) is None:
            raise NotFoundError(f"organization not found: {organization_id}")
        now = datetime.now(tz=UTC)
        kb = KnowledgeBase(
            id=uuid4(),
            organization_id=organization_id,
            name=name,
            created_at=now,
            updated_at=now,
        )
        self._by_id[kb.id] = kb
        self._by_org.setdefault(organization_id, []).append(kb)
        return kb

    async def get_by_id(self, knowledge_base_id: UUID) -> KnowledgeBase | None:
        return self._by_id.get(knowledge_base_id)

    async def list_for_organization(self, organization_id: UUID) -> list[KnowledgeBase]:
        return list(self._by_org.get(organization_id, []))
