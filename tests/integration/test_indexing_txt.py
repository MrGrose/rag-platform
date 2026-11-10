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
async def test_txt_upload_produces_chunks_and_vectors() -> None:
    storage = InMemoryObjectStorage()

    async def noop_enqueue(_doc_id, _kb, _org) -> None:
        return None

    async with session_scope() as session:
        org_repo = SqlAlchemyOrganizationRepository(session)
        org = await org_repo.create(f"index-{uuid4().hex[:8]}")
        kb_repo = SqlAlchemyKnowledgeBaseRepository(session)
        kb = await kb_repo.create(org.id, "kb")
        doc_repo = SqlAlchemyDocumentRepository(session)
        chunk_repo = SqlAlchemyChunkRepository(session)
        create = CreateDocument(
            kb_repo=kb_repo,
            doc_repo=doc_repo,
            storage=storage,
            kb_version=NoopKnowledgeBaseVersion(),
            enqueue_process=noop_enqueue,
        )
        text = b"RAG platform indexing test. " * 20
        doc = await create.execute(
            knowledge_base_id=kb.id,
            filename="sample.txt",
            mime_type="text/plain",
            content=text,
        )
        processor = ProcessDocument(
            doc_repo=doc_repo,
            chunk_repo=chunk_repo,
            storage=storage,
            embeddings=FakeEmbeddingProvider(),
            parsers=default_parser_registry(),
        )
        ready = await processor.execute(doc.id)
        assert ready.status == DocumentStatus.READY
        chunks = await chunk_repo.list_for_document(doc.id)
        assert chunks
        assert all(len(chunk.embedding) == FakeEmbeddingProvider.dimension for chunk in chunks)
        assert all(chunk.page == 1 for chunk in chunks)
