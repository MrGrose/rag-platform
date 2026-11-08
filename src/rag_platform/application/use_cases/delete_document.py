from collections.abc import Awaitable, Callable
from datetime import UTC, datetime
from uuid import UUID

from rag_platform.application.ports.documents import DocumentRepository
from rag_platform.application.ports.kb_version import KnowledgeBaseVersionPort
from rag_platform.domain.entities import Document
from rag_platform.domain.errors import NotFoundError

EnqueueDeleteVectors = Callable[[UUID, UUID, UUID], Awaitable[None]]


class DeleteDocument:
    def __init__(
        self,
        *,
        doc_repo: DocumentRepository,
        kb_version: KnowledgeBaseVersionPort,
        enqueue_cleanup: EnqueueDeleteVectors,
    ) -> None:
        self._doc_repo = doc_repo
        self._kb_version = kb_version
        self._enqueue_cleanup = enqueue_cleanup

    async def execute(self, *, document_id: UUID, knowledge_base_id: UUID) -> Document:
        document = await self._doc_repo.get_by_id(document_id)
        if document is None or document.knowledge_base_id != knowledge_base_id:
            raise NotFoundError(f"document not found: {document_id}")
        now = datetime.now(tz=UTC)
        updated = Document(
            id=document.id,
            knowledge_base_id=document.knowledge_base_id,
            organization_id=document.organization_id,
            filename=document.filename,
            mime_type=document.mime_type,
            size_bytes=document.size_bytes,
            status=document.status,
            storage_key=document.storage_key,
            content_hash=document.content_hash,
            content_version=document.content_version,
            error_message=document.error_message,
            deleted_at=now,
            created_at=document.created_at,
            updated_at=now,
            processing_started_at=document.processing_started_at,
        )
        saved = await self._doc_repo.save(updated)
        await self._kb_version.bump(str(knowledge_base_id))
        await self._enqueue_cleanup(saved.id, saved.knowledge_base_id, saved.organization_id)
        return saved
