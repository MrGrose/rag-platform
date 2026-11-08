from uuid import UUID

import pytest

from rag_platform.application.use_cases.create_document import CreateDocument
from rag_platform.domain.entities import Document
from rag_platform.domain.enums import DocumentStatus
from rag_platform.infrastructure.fakes.kb_version import NoopKnowledgeBaseVersion
from rag_platform.infrastructure.fakes.repositories import (
    InMemoryKnowledgeBaseRepository,
    InMemoryOrganizationRepository,
)
from rag_platform.infrastructure.fakes.storage import InMemoryObjectStorage


class InMemoryDocumentRepository:
    def __init__(self) -> None:
        self._by_id: dict[UUID, Document] = {}
        self._by_hash: dict[tuple[UUID, str], Document] = {}

    async def create(self, document: Document) -> Document:
        self._by_id[document.id] = document
        self._by_hash[(document.knowledge_base_id, document.content_hash)] = document
        return document

    async def get_by_id(self, document_id: UUID) -> Document | None:
        return self._by_id.get(document_id)

    async def list_for_knowledge_base(self, knowledge_base_id: UUID) -> list[Document]:
        return [d for d in self._by_id.values() if d.knowledge_base_id == knowledge_base_id]

    async def get_by_content_hash(
        self,
        knowledge_base_id: UUID,
        content_hash: str,
    ) -> Document | None:
        return self._by_hash.get((knowledge_base_id, content_hash))

    async def save(self, document: Document) -> Document:
        self._by_id[document.id] = document
        self._by_hash[(document.knowledge_base_id, document.content_hash)] = document
        return document


async def _noop_enqueue(_document_id: UUID, _kb: UUID, _org: UUID) -> None:
    return None


@pytest.mark.asyncio
async def test_create_document_stores_blob_and_enqueues() -> None:
    org_repo = InMemoryOrganizationRepository()
    org = await org_repo.create("acme")
    kb_repo = InMemoryKnowledgeBaseRepository(org_repo)
    kb = await kb_repo.create(org.id, "main")
    storage = InMemoryObjectStorage()
    enqueued: list[UUID] = []
    doc_repo = InMemoryDocumentRepository()

    async def track_enqueue(document_id: UUID, _kb: UUID, _org: UUID) -> None:
        enqueued.append(document_id)

    use_case = CreateDocument(
        kb_repo=kb_repo,
        doc_repo=doc_repo,
        storage=storage,
        kb_version=NoopKnowledgeBaseVersion(),
        enqueue_process=track_enqueue,
    )
    saved = await use_case.execute(
        knowledge_base_id=kb.id,
        filename="hello.txt",
        mime_type="text/plain",
        content=b"hello",
    )
    assert saved.status == DocumentStatus.UPLOADED
    assert enqueued == [saved.id]
    assert await storage.object_exists(saved.storage_key)


@pytest.mark.asyncio
async def test_create_document_idempotent_on_same_hash() -> None:
    org_repo = InMemoryOrganizationRepository()
    org = await org_repo.create("acme")
    kb_repo = InMemoryKnowledgeBaseRepository(org_repo)
    kb = await kb_repo.create(org.id, "main")
    storage = InMemoryObjectStorage()
    doc_repo = InMemoryDocumentRepository()
    use_case = CreateDocument(
        kb_repo=kb_repo,
        doc_repo=doc_repo,
        storage=storage,
        kb_version=NoopKnowledgeBaseVersion(),
        enqueue_process=_noop_enqueue,
    )
    first = await use_case.execute(
        knowledge_base_id=kb.id,
        filename="a.txt",
        mime_type="text/plain",
        content=b"same",
    )
    second = await use_case.execute(
        knowledge_base_id=kb.id,
        filename="b.txt",
        mime_type="text/plain",
        content=b"same",
    )
    assert first.id == second.id


@pytest.mark.asyncio
async def test_duplicate_upload_reenqueues_failed_document() -> None:
    org_repo = InMemoryOrganizationRepository()
    org = await org_repo.create("acme")
    kb_repo = InMemoryKnowledgeBaseRepository(org_repo)
    kb = await kb_repo.create(org.id, "main")
    storage = InMemoryObjectStorage()
    doc_repo = InMemoryDocumentRepository()
    enqueued: list[UUID] = []

    async def track_enqueue(document_id: UUID, _kb: UUID, _org: UUID) -> None:
        enqueued.append(document_id)

    use_case = CreateDocument(
        kb_repo=kb_repo,
        doc_repo=doc_repo,
        storage=storage,
        kb_version=NoopKnowledgeBaseVersion(),
        enqueue_process=track_enqueue,
    )
    first = await use_case.execute(
        knowledge_base_id=kb.id,
        filename="a.txt",
        mime_type="text/plain",
        content=b"same",
    )
    failed = Document(
        id=first.id,
        knowledge_base_id=first.knowledge_base_id,
        organization_id=first.organization_id,
        filename=first.filename,
        mime_type=first.mime_type,
        size_bytes=first.size_bytes,
        status=DocumentStatus.FAILED,
        storage_key=first.storage_key,
        content_hash=first.content_hash,
        content_version=first.content_version,
        error_message="parse error",
        deleted_at=None,
        created_at=first.created_at,
        updated_at=first.updated_at,
        processing_started_at=None,
    )
    await doc_repo.save(failed)
    enqueued.clear()
    await use_case.execute(
        knowledge_base_id=kb.id,
        filename="b.txt",
        mime_type="text/plain",
        content=b"same",
    )
    assert enqueued == [first.id]
