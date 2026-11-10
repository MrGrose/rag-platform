from pathlib import Path
from uuid import UUID, uuid4

import pytest
from sqlalchemy import text

from rag_platform.application.use_cases.create_document import CreateDocument
from rag_platform.application.use_cases.process_document import ProcessDocument
from rag_platform.infrastructure.db.chunk_repository import SqlAlchemyChunkRepository
from rag_platform.infrastructure.db.document_repository import SqlAlchemyDocumentRepository
from rag_platform.infrastructure.db.repositories import (
    SqlAlchemyKnowledgeBaseRepository,
    SqlAlchemyOrganizationRepository,
)
from rag_platform.infrastructure.db.retrieval_engine import PgHybridRetrievalEngine
from rag_platform.infrastructure.db.session import session_scope
from rag_platform.infrastructure.fakes.kb_version import NoopKnowledgeBaseVersion
from rag_platform.infrastructure.fakes.storage import InMemoryObjectStorage
from rag_platform.infrastructure.parsing.registry import default_parser_registry
from rag_platform.infrastructure.providers.fake_embeddings import FakeEmbeddingProvider

ROOT = Path(__file__).resolve().parents[2]
PDF = ROOT / "examples" / "corpus_pdf" / "refund-policy.pdf"


async def _seed() -> tuple[UUID, UUID]:
    storage = InMemoryObjectStorage()

    async def noop(_doc_id, _kb, _org) -> None:
        return None

    async with session_scope() as session:
        org = await SqlAlchemyOrganizationRepository(session).create(f"pdf-{uuid4().hex[:8]}")
        kb = await SqlAlchemyKnowledgeBaseRepository(session).create(org.id, "pdf-kb")
        doc_repo = SqlAlchemyDocumentRepository(session)
        document = await CreateDocument(
            kb_repo=SqlAlchemyKnowledgeBaseRepository(session),
            doc_repo=doc_repo,
            storage=storage,
            kb_version=NoopKnowledgeBaseVersion(),
            enqueue_process=noop,
        ).execute(
            knowledge_base_id=kb.id,
            filename="refund-policy.pdf",
            mime_type="application/pdf",
            content=PDF.read_bytes(),
        )
        await ProcessDocument(
            doc_repo=doc_repo,
            chunk_repo=SqlAlchemyChunkRepository(session),
            storage=storage,
            embeddings=FakeEmbeddingProvider(),
            parsers=default_parser_registry(),
        ).execute(document.id)
        return org.id, kb.id


@pytest.mark.integration
@pytest.mark.asyncio
async def test_pdf_chunks_keep_page_numbers() -> None:
    _org_id, kb_id = await _seed()
    async with session_scope() as session:
        rows = await session.execute(
            text(
                "SELECT content, page FROM document_chunks "
                "WHERE knowledge_base_id = :kb_id ORDER BY chunk_index"
            ),
            {"kb_id": kb_id},
        )
        chunks = rows.all()

    assert chunks
    assert {page for _content, page in chunks} == {1, 2}
    electronics = [content for content, page in chunks if page == 2 and "Electronics" in content]
    assert electronics


@pytest.mark.integration
@pytest.mark.asyncio
async def test_pdf_retrieval_reports_the_page() -> None:
    org_id, kb_id = await _seed()
    async with session_scope() as session:
        engine = PgHybridRetrievalEngine(session, FakeEmbeddingProvider(), mode="hybrid")
        hits = await engine.retrieve(
            organization_id=org_id,
            knowledge_base_id=kb_id,
            question="How many days are electronics refundable with original packaging?",
            limit=5,
        )

    assert hits
    assert any(hit.page == 2 for hit in hits)
    assert any("14 days" in hit.content and hit.page == 2 for hit in hits)
