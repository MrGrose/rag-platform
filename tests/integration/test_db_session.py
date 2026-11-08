from uuid import uuid4

import pytest

from rag_platform.infrastructure.db.repositories import (
    SqlAlchemyKnowledgeBaseRepository,
    SqlAlchemyOrganizationRepository,
)
from rag_platform.infrastructure.db.session import session_scope


@pytest.mark.integration
@pytest.mark.asyncio
async def test_db_session_roundtrip_persists_org_and_kb() -> None:
    suffix = uuid4().hex[:12]
    org_name = f"integration-test-org-{suffix}"
    kb_name = f"integration-test-kb-{suffix}"
    org_id = None
    kb_id = None
    async with session_scope() as session:
        org_repo = SqlAlchemyOrganizationRepository(session)
        kb_repo = SqlAlchemyKnowledgeBaseRepository(session)
        org = await org_repo.create(org_name)
        kb = await kb_repo.create(org.id, kb_name)
        org_id = org.id
        kb_id = kb.id
        assert kb.organization_id == org.id

    async with session_scope() as session:
        org_repo = SqlAlchemyOrganizationRepository(session)
        kb_repo = SqlAlchemyKnowledgeBaseRepository(session)
        loaded_org = await org_repo.get_by_name(org_name)
        assert loaded_org is not None
        listed = await kb_repo.list_for_organization(loaded_org.id)
        assert any(item.id == kb_id for item in listed)
        assert loaded_org.id == org_id
