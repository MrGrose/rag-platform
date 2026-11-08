from uuid import uuid4

import pytest

from rag_platform.application.use_cases.create_document import CreateDocument
from rag_platform.application.use_cases.process_document import ProcessDocument
from rag_platform.domain.enums import DocumentStatus
from rag_platform.infrastructure.db.chunk_repository import SqlAlchemyChunkRepository
from rag_platform.infrastructure.db.document_repository import SqlAlchemyDocumentRepository
from rag_platform.infrastructure.db.repositories import (
    SqlAlchemyKnowledgeBaseRepository,
    SqlAlchemyOrganizationRepository,
)
from rag_platform.infrastructure.db.session import session_scope
from rag_platform.infrastructure.fakes.kb_version import NoopKnowledgeBaseVersion
from rag_platform.infrastructure.fakes.storage import InMemoryObjectStorage
from rag_platform.infrastructure.parsing.registry import default_parser_registry
from rag_platform.infrastructure.providers.fake_embeddings import FakeEmbeddingProvider


@pytest.mark.integration
@pytest.mark.asyncio
async def test_corrupt_pdf_marks_failed() -> None:
    storage = InMemoryObjectStorage()

    async def noop(_: object, _kb, _org) -> None:
        return None

    async with session_scope() as session:
        org = await SqlAlchemyOrganizationRepository(session).create(f"fail-{uuid4().hex[:8]}")
        kb_repo = SqlAlchemyKnowledgeBaseRepository(session)
        kb = await kb_repo.create(org.id, "kb")
        doc_repo = SqlAlchemyDocumentRepository(session)
        doc = await CreateDocument(
            kb_repo=kb_repo,
            doc_repo=doc_repo,
            storage=storage,
            kb_version=NoopKnowledgeBaseVersion(),
            enqueue_process=noop,
        ).execute(
            knowledge_base_id=kb.id,
            filename="bad.pdf",
            mime_type="application/pdf",
            content=b"not-a-pdf",
        )
        result = await ProcessDocument(
            doc_repo=doc_repo,
            chunk_repo=SqlAlchemyChunkRepository(session),
            storage=storage,
            embeddings=FakeEmbeddingProvider(),
            parsers=default_parser_registry(),
        ).execute(doc.id)
        assert result.status == DocumentStatus.FAILED
        assert result.error_message
