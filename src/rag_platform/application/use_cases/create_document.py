import hashlib
from collections.abc import Awaitable, Callable
from datetime import UTC, datetime, timedelta
from uuid import UUID, uuid4

from sqlalchemy.exc import IntegrityError

from rag_platform.application.ports.documents import DocumentRepository
from rag_platform.application.ports.kb_version import KnowledgeBaseVersionPort
from rag_platform.application.ports.repositories import KnowledgeBaseRepository
from rag_platform.application.ports.storage import ObjectStorage
from rag_platform.application.validation.upload import validate_upload
from rag_platform.config import get_settings
from rag_platform.domain.entities import Document
from rag_platform.domain.enums import DocumentStatus
from rag_platform.domain.errors import NotFoundError

EnqueueProcessDocument = Callable[[UUID, UUID, UUID], Awaitable[None]]


class CreateDocument:
    def __init__(
        self,
        *,
        kb_repo: KnowledgeBaseRepository,
        doc_repo: DocumentRepository,
        storage: ObjectStorage,
        kb_version: KnowledgeBaseVersionPort,
        enqueue_process: EnqueueProcessDocument,
    ) -> None:
        self._kb_repo = kb_repo
        self._doc_repo = doc_repo
        self._storage = storage
        self._kb_version = kb_version
        self._enqueue_process = enqueue_process

    async def _maybe_reenqueue(self, document: Document) -> bool:
        if document.status == DocumentStatus.FAILED:
            return True
        if document.status == DocumentStatus.UPLOADED:
            stale_after = timedelta(seconds=get_settings().processing_stale_seconds)
            return datetime.now(tz=UTC) - document.updated_at >= stale_after
        if document.status == DocumentStatus.PROCESSING:
            stale_after = timedelta(seconds=get_settings().processing_stale_seconds)
            started = document.processing_started_at or document.updated_at
            return datetime.now(tz=UTC) - started >= stale_after
        return False

    async def _finalize_existing(self, document: Document) -> Document:
        if document.deleted_at is not None:
            return document
        if await self._maybe_reenqueue(document):
            await self._enqueue_process(
                document.id,
                document.knowledge_base_id,
                document.organization_id,
            )
        return document

    async def execute(
        self,
        *,
        knowledge_base_id: UUID,
        filename: str,
        mime_type: str,
        content: bytes,
    ) -> Document:
        kb = await self._kb_repo.get_by_id(knowledge_base_id)
        if kb is None:
            raise NotFoundError(f"knowledge base not found: {knowledge_base_id}")
        safe_name = validate_upload(filename, mime_type, len(content))
        content_hash = hashlib.sha256(content).hexdigest()
        existing = await self._doc_repo.get_by_content_hash(knowledge_base_id, content_hash)
        if existing is not None:
            return await self._finalize_existing(existing)
        doc_id = uuid4()
        storage_key = f"{kb.organization_id}/{knowledge_base_id}/{doc_id}/{safe_name}"
        await self._storage.put_object(storage_key, content, mime_type)
        now = datetime.now(tz=UTC)
        document = Document(
            id=doc_id,
            knowledge_base_id=knowledge_base_id,
            organization_id=kb.organization_id,
            filename=safe_name,
            mime_type=mime_type,
            size_bytes=len(content),
            status=DocumentStatus.UPLOADED,
            storage_key=storage_key,
            content_hash=content_hash,
            content_version=1,
            error_message=None,
            deleted_at=None,
            created_at=now,
            updated_at=now,
        )
        try:
            saved = await self._doc_repo.create(document)
        except IntegrityError:
            again = await self._doc_repo.get_by_content_hash(knowledge_base_id, content_hash)
            if again is None:
                raise
            return await self._finalize_existing(again)
        await self._enqueue_process(saved.id, saved.knowledge_base_id, saved.organization_id)
        await self._kb_version.bump(str(knowledge_base_id))
        return saved
