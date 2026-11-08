from uuid import uuid4

import pytest

from rag_platform.application.use_cases.create_document import CreateDocument
from rag_platform.infrastructure.db.document_repository import SqlAlchemyDocumentRepository
from rag_platform.infrastructure.db.repositories import (
    SqlAlchemyKnowledgeBaseRepository,
    SqlAlchemyOrganizationRepository,
)
from rag_platform.infrastructure.db.session import session_scope
from rag_platform.infrastructure.fakes.kb_version import NoopKnowledgeBaseVersion
from rag_platform.infrastructure.fakes.storage import InMemoryObjectStorage


@pytest.mark.integration
@pytest.mark.asyncio
async def test_upload_idempotency_same_hash() -> None:
    storage = InMemoryObjectStorage()
    enqueue_count = 0

    async def track(_doc_id, _kb, _org) -> None:
        nonlocal enqueue_count
        enqueue_count += 1

    async with session_scope() as session:
        org_repo = SqlAlchemyOrganizationRepository(session)
        org = await org_repo.create(f"idempotency-{uuid4().hex[:8]}")
        kb_repo = SqlAlchemyKnowledgeBaseRepository(session)
        kb = await kb_repo.create(org.id, "kb")
        use_case = CreateDocument(
            kb_repo=kb_repo,
            doc_repo=SqlAlchemyDocumentRepository(session),
            storage=storage,
            kb_version=NoopKnowledgeBaseVersion(),
            enqueue_process=track,
        )
        first = await use_case.execute(
            knowledge_base_id=kb.id,
            filename="a.txt",
            mime_type="text/plain",
            content=b"same-content",
        )
        second = await use_case.execute(
            knowledge_base_id=kb.id,
            filename="b.txt",
            mime_type="text/plain",
            content=b"same-content",
        )
    assert first.id == second.id
    assert enqueue_count == 1
