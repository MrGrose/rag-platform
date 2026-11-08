from datetime import UTC, datetime, timedelta
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from rag_platform.application.ports.documents import DocumentRepository
from rag_platform.domain.entities import Document
from rag_platform.domain.enums import DocumentStatus
from rag_platform.infrastructure.db.models import DocumentModel


def _to_document(row: DocumentModel) -> Document:
    return Document(
        id=row.id,
        knowledge_base_id=row.knowledge_base_id,
        organization_id=row.organization_id,
        filename=row.filename,
        mime_type=row.mime_type,
        size_bytes=row.size_bytes,
        status=DocumentStatus(row.status),
        storage_key=row.storage_key,
        content_hash=row.content_hash,
        content_version=row.content_version,
        error_message=row.error_message,
        deleted_at=row.deleted_at,
        created_at=row.created_at,
        updated_at=row.updated_at,
        processing_started_at=row.processing_started_at,
    )


def _apply_row(row: DocumentModel, document: Document) -> None:
    row.knowledge_base_id = document.knowledge_base_id
    row.organization_id = document.organization_id
    row.filename = document.filename
    row.mime_type = document.mime_type
    row.size_bytes = document.size_bytes
    row.status = str(document.status)
    row.storage_key = document.storage_key
    row.content_hash = document.content_hash
    row.content_version = document.content_version
    row.error_message = document.error_message
    row.deleted_at = document.deleted_at
    row.processing_started_at = document.processing_started_at


class SqlAlchemyDocumentRepository(DocumentRepository):
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create(self, document: Document) -> Document:
        row = DocumentModel()
        _apply_row(row, document)
        row.id = document.id
        self._session.add(row)
        await self._session.flush()
        await self._session.refresh(row)
        return _to_document(row)

    async def get_by_id(self, document_id: UUID) -> Document | None:
        row = await self._session.get(DocumentModel, document_id)
        if row is None or row.deleted_at is not None:
            return None
        return _to_document(row)

    async def get_by_id_for_kb(
        self,
        document_id: UUID,
        knowledge_base_id: UUID,
    ) -> Document | None:
        document = await self.get_by_id(document_id)
        if document is None or document.knowledge_base_id != knowledge_base_id:
            return None
        return document

    async def list_for_knowledge_base(self, knowledge_base_id: UUID) -> list[Document]:
        stmt = select(DocumentModel).where(
            DocumentModel.knowledge_base_id == knowledge_base_id,
            DocumentModel.deleted_at.is_(None),
        )
        result = await self._session.execute(stmt)
        return [_to_document(row) for row in result.scalars().all()]

    async def get_by_content_hash(
        self,
        knowledge_base_id: UUID,
        content_hash: str,
    ) -> Document | None:
        stmt = select(DocumentModel).where(
            DocumentModel.knowledge_base_id == knowledge_base_id,
            DocumentModel.content_hash == content_hash,
            DocumentModel.deleted_at.is_(None),
        )
        result = await self._session.execute(stmt)
        row = result.scalar_one_or_none()
        if row is None:
            return None
        return _to_document(row)

    async def save(self, document: Document) -> Document:
        row = await self._session.get(DocumentModel, document.id)
        if row is None:
            raise ValueError(f"document not found: {document.id}")
        _apply_row(row, document)
        await self._session.flush()
        await self._session.refresh(row)
        return _to_document(row)

    async def list_stale_for_requeue(self, stale_seconds: int) -> list[Document]:
        cutoff = datetime.now(tz=UTC) - timedelta(seconds=stale_seconds)
        stmt = select(DocumentModel).where(
            DocumentModel.deleted_at.is_(None),
            DocumentModel.status.in_(("uploaded", "processing")),
        )
        result = await self._session.execute(stmt)
        rows = list(result.scalars().all())
        stale: list[Document] = []
        for row in rows:
            started = row.processing_started_at or row.updated_at
            if started is None or started <= cutoff:
                stale.append(_to_document(row))
        return stale
