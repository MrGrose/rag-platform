from typing import Protocol
from uuid import UUID

from rag_platform.domain.entities import KnowledgeBase, Organization


class OrganizationRepository(Protocol):
    async def create(self, name: str) -> Organization: ...

    async def get_by_id(self, organization_id: UUID) -> Organization | None: ...

    async def get_by_name(self, name: str) -> Organization | None: ...


class KnowledgeBaseRepository(Protocol):
    async def create(self, organization_id: UUID, name: str) -> KnowledgeBase: ...

    async def get_by_id(self, knowledge_base_id: UUID) -> KnowledgeBase | None: ...

    async def list_for_organization(self, organization_id: UUID) -> list[KnowledgeBase]: ...
