from uuid import uuid4

import pytest

from rag_platform.domain.errors import ConflictError, NotFoundError
from rag_platform.infrastructure.fakes.repositories import (
    InMemoryKnowledgeBaseRepository,
    InMemoryOrganizationRepository,
)


@pytest.mark.asyncio
async def test_in_memory_org_and_kb_roundtrip() -> None:
    org_repo = InMemoryOrganizationRepository()
    kb_repo = InMemoryKnowledgeBaseRepository(org_repo)
    org = await org_repo.create("acme")
    kb = await kb_repo.create(org.id, "default")
    assert await org_repo.get_by_id(org.id) == org
    assert await kb_repo.get_by_id(kb.id) == kb
    listed = await kb_repo.list_for_organization(org.id)
    assert len(listed) == 1


@pytest.mark.asyncio
async def test_in_memory_org_create_conflict() -> None:
    org_repo = InMemoryOrganizationRepository()
    await org_repo.create("acme")
    with pytest.raises(ConflictError):
        await org_repo.create("acme")


@pytest.mark.asyncio
async def test_in_memory_kb_requires_org() -> None:
    org_repo = InMemoryOrganizationRepository()
    kb_repo = InMemoryKnowledgeBaseRepository(org_repo)
    with pytest.raises(NotFoundError):
        await kb_repo.create(uuid4(), "orphan")
