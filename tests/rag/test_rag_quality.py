from uuid import uuid4

import pytest
from httpx import ASGITransport, AsyncClient

from rag_platform.api.app import create_app
from rag_platform.api.deps import get_db_session, get_object_storage
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
from rag_platform.infrastructure.parsing.registry import default_parser_registry
from rag_platform.infrastructure.providers.fake_embeddings import FakeEmbeddingProvider


async def _seed_kb_with_doc(*, phrase: str) -> tuple[object, object, object]:
    storage = InMemoryObjectStorage()
    kb_id = None
    org_id = None
    async with session_scope() as session:
        org = await SqlAlchemyOrganizationRepository(session).create(f"org-{uuid4().hex[:6]}")
        org_id = org.id
        kb_repo = SqlAlchemyKnowledgeBaseRepository(session)
        kb = await kb_repo.create(org.id, "rag-kb")
        kb_id = kb.id
        doc_repo = SqlAlchemyDocumentRepository(session)
        chunk_repo = SqlAlchemyChunkRepository(session)

        async def noop(_: object, _kb, _org) -> None:
            return None

        doc = await CreateDocument(
            kb_repo=kb_repo,
            doc_repo=doc_repo,
            storage=storage,
            kb_version=NoopKnowledgeBaseVersion(),
            enqueue_process=noop,
        ).execute(
            knowledge_base_id=kb.id,
            filename="facts.txt",
            mime_type="text/plain",
            content=f"Indexed fact: {phrase}.".encode(),
        )
        await ProcessDocument(
            doc_repo=doc_repo,
            chunk_repo=chunk_repo,
            storage=storage,
            embeddings=FakeEmbeddingProvider(),
            parsers=default_parser_registry(),
        ).execute(doc.id)
    return storage, org_id, kb_id


@pytest.mark.rag
@pytest.mark.integration
@pytest.mark.asyncio
async def test_tenant_isolation_wrong_org_header() -> None:
    phrase = f"tenant-{uuid4().hex[:8]}"
    storage, _org_id, kb_id = await _seed_kb_with_doc(phrase=phrase)
    other_org = uuid4()

    async def override_session():
        async with session_scope() as session:
            yield session

    app = create_app()
    app.dependency_overrides[get_db_session] = override_session
    app.dependency_overrides[get_object_storage] = lambda: storage

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post(
            "/v1/chat",
            json={"knowledge_base_id": str(kb_id), "question": "Indexed fact"},
            headers={"X-Organization-Id": str(other_org)},
        )
        assert response.status_code == 422


@pytest.mark.rag
@pytest.mark.integration
@pytest.mark.asyncio
async def test_insufficient_context_empty_kb() -> None:
    storage = InMemoryObjectStorage()
    kb_id = None
    org_id = None
    async with session_scope() as session:
        org = await SqlAlchemyOrganizationRepository(session).create(f"empty-{uuid4().hex[:6]}")
        org_id = org.id
        kb = await SqlAlchemyKnowledgeBaseRepository(session).create(org.id, "empty-kb")
        kb_id = kb.id

    async def override_session():
        async with session_scope() as session:
            yield session

    app = create_app()
    app.dependency_overrides[get_db_session] = override_session
    app.dependency_overrides[get_object_storage] = lambda: storage

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post(
            "/v1/chat",
            json={"knowledge_base_id": str(kb_id), "question": "anything"},
            headers={"X-Organization-Id": str(org_id)},
        )
        assert response.status_code == 200
        assert response.json()["insufficient_context"] is True


@pytest.mark.rag
@pytest.mark.integration
@pytest.mark.asyncio
async def test_citation_chunk_ids_match_indexed_doc() -> None:
    phrase = f"citation-{uuid4().hex[:8]}"
    storage, org_id, kb_id = await _seed_kb_with_doc(phrase=phrase)

    async def override_session():
        async with session_scope() as session:
            yield session

    app = create_app()
    app.dependency_overrides[get_db_session] = override_session
    app.dependency_overrides[get_object_storage] = lambda: storage

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post(
            "/v1/chat",
            json={"knowledge_base_id": str(kb_id), "question": phrase},
            headers={"X-Organization-Id": str(org_id)},
        )
        assert response.status_code == 200
        body = response.json()
        assert body["citations"]
        for citation in body["citations"]:
            assert citation["chunk_id"]
            assert citation["document_id"]
