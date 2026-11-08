from uuid import uuid4

import pytest

from rag_platform.application.use_cases.create_document import CreateDocument
from rag_platform.infrastructure.db.document_repository import SqlAlchemyDocumentRepository
from rag_platform.infrastructure.db.repositories import SqlAlchemyOrganizationRepository
from rag_platform.infrastructure.db.session import session_scope
from rag_platform.infrastructure.fakes.kb_version import NoopKnowledgeBaseVersion
from rag_platform.infrastructure.fakes.storage import InMemoryObjectStorage


@pytest.mark.integration
@pytest.mark.asyncio
async def test_upload_persists_row_and_object() -> None:
    storage = InMemoryObjectStorage()
    enqueued: list = []

    async def track(_doc_id, _kb, _org) -> None:
        enqueued.append(_doc_id)

    async with session_scope() as session:
        org_repo = SqlAlchemyOrganizationRepository(session)
        org = await org_repo.create(f"upload-flow-{uuid4().hex[:8]}")
        from rag_platform.infrastructure.db.repositories import SqlAlchemyKnowledgeBaseRepository

        kb_repo = SqlAlchemyKnowledgeBaseRepository(session)
        kb = await kb_repo.create(org.id, "kb")
        use_case = CreateDocument(
            kb_repo=kb_repo,
            doc_repo=SqlAlchemyDocumentRepository(session),
            storage=storage,
            kb_version=NoopKnowledgeBaseVersion(),
            enqueue_process=track,
        )
        doc = await use_case.execute(
            knowledge_base_id=kb.id,
            filename="note.txt",
            mime_type="text/plain",
            content=b"integration upload",
        )
        assert doc.id in enqueued
        assert await storage.object_exists(doc.storage_key)
        loaded = await SqlAlchemyDocumentRepository(session).get_by_id(doc.id)
        assert loaded is not None
