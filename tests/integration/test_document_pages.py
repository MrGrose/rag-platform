from uuid import uuid4

import pytest

from rag_platform.application.use_cases.create_document import CreateDocument
from rag_platform.application.use_cases.process_document import ProcessDocument
from rag_platform.infrastructure.db.chunk_repository import SqlAlchemyChunkRepository
from rag_platform.infrastructure.db.document_repository import SqlAlchemyDocumentRepository
from rag_platform.infrastructure.db.repositories import (
    SqlAlchemyKnowledgeBaseRepository,
    SqlAlchemyOrganizationRepository,
)
from rag_platform.infrastructure.db.session import session_scope
from rag_platform.infrastructure.fakes.kb_version import NoopKnowledgeBaseVersion
from rag_platform.infrastructure.fakes.storage import InMemoryObjectStorage
from rag_platform.infrastructure.providers.fake_embeddings import FakeEmbeddingProvider


class _PagedRegistry:
    def __init__(self, pages: list[tuple[int, str]]) -> None:
        self._pages = pages

    def parse(self, mime_type: str, content: bytes) -> str:
        return "\n".join(text for _page, text in self._pages)

    def parse_pages(self, mime_type: str, content: bytes) -> list[tuple[int, str]]:
        return self._pages


@pytest.mark.integration
@pytest.mark.asyncio
async def test_chunks_keep_the_page_they_came_from() -> None:
    storage = InMemoryObjectStorage()

    async def noop(_doc_id, _kb, _org) -> None:
        return None

    async with session_scope() as session:
        org = await SqlAlchemyOrganizationRepository(session).create(f"pages-{uuid4().hex[:8]}")
        kb = await SqlAlchemyKnowledgeBaseRepository(session).create(org.id, "kb")
        doc_repo = SqlAlchemyDocumentRepository(session)
        chunk_repo = SqlAlchemyChunkRepository(session)
        document = await CreateDocument(
            kb_repo=SqlAlchemyKnowledgeBaseRepository(session),
            doc_repo=doc_repo,
            storage=storage,
            kb_version=NoopKnowledgeBaseVersion(),
            enqueue_process=noop,
        ).execute(
            knowledge_base_id=kb.id,
            filename="two-pages.txt",
            mime_type="text/plain",
            content=b"stored content",
        )
        registry = _PagedRegistry(
            [
                (1, "First page about refunds. " * 30),
                (2, "Second page about delivery. " * 30),
            ]
        )
        await ProcessDocument(
            doc_repo=doc_repo,
            chunk_repo=chunk_repo,
            storage=storage,
            embeddings=FakeEmbeddingProvider(),
            parsers=registry,
        ).execute(document.id)
        chunks = await chunk_repo.list_for_document(document.id)

    assert chunks
    assert {chunk.page for chunk in chunks} == {1, 2}
    assert chunks[0].page == 1
    assert chunks[-1].page == 2
