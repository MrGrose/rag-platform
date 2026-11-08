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


@pytest.mark.rag
@pytest.mark.integration
@pytest.mark.asyncio
async def test_mvp_e2e_upload_index_chat() -> None:
    storage = InMemoryObjectStorage()

    async def override_session():
        async with session_scope() as session:
            yield session

    app = create_app()
    app.dependency_overrides[get_db_session] = override_session
    app.dependency_overrides[get_object_storage] = lambda: storage

    phrase = f"mvp-e2e-token-{uuid4().hex}"
    kb_id = None
    org_id = None

    async with session_scope() as session:
        org = await SqlAlchemyOrganizationRepository(session).create(f"mvp-{uuid4().hex[:6]}")
        org_id = org.id
        kb_repo = SqlAlchemyKnowledgeBaseRepository(session)
        kb = await kb_repo.create(org.id, "mvp-kb")
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
            content=f"The secret keyword is {phrase}.".encode(),
        )
        await ProcessDocument(
            doc_repo=doc_repo,
            chunk_repo=chunk_repo,
            storage=storage,
            embeddings=FakeEmbeddingProvider(),
            parsers=default_parser_registry(),
        ).execute(doc.id)

    headers = {"X-Organization-Id": str(org_id)}
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        chat = await client.post(
            "/v1/chat",
            json={"knowledge_base_id": str(kb_id), "question": phrase},
            headers=headers,
        )
        assert chat.status_code == 200, chat.text
        body = chat.json()
        assert body["answer"]
        assert not body["insufficient_context"]
        assert body["citations"]
        query_id = body["query_id"]
        audit = await client.get(
            f"/v1/queries/{query_id}",
            params={"knowledge_base_id": str(kb_id)},
            headers=headers,
        )
        assert audit.status_code == 200
        assert audit.json()["retrieval_results"]
