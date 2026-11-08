from datetime import UTC, datetime, timedelta
from uuid import UUID, uuid4

from rag_platform.application.ports.chunks import ChunkRepository
from rag_platform.application.ports.documents import DocumentRepository
from rag_platform.application.ports.embeddings import EmbeddingProvider
from rag_platform.application.ports.parsing import MimeParserRegistry
from rag_platform.application.ports.storage import ObjectStorage
from rag_platform.application.processing.chunking import ChunkingConfig, chunk_text
from rag_platform.application.processing.normalize import assert_text_within_limit, normalize_text
from rag_platform.config import get_settings
from rag_platform.domain.constants import (
    CHUNK_OVERLAP,
    CHUNK_SIZE,
    MAX_CHUNK_COUNT,
    MAX_DOCUMENT_TEXT_BYTES,
)
from rag_platform.domain.entities import Document, DocumentChunk
from rag_platform.domain.enums import DocumentStatus
from rag_platform.domain.errors import NotFoundError, ValidationError


class ProcessDocument:
    def __init__(
        self,
        *,
        doc_repo: DocumentRepository,
        chunk_repo: ChunkRepository,
        storage: ObjectStorage,
        embeddings: EmbeddingProvider,
        parsers: MimeParserRegistry,
    ) -> None:
        self._doc_repo = doc_repo
        self._chunk_repo = chunk_repo
        self._storage = storage
        self._embeddings = embeddings
        self._parsers = parsers

    async def execute(self, document_id: UUID) -> Document:
        document = await self._doc_repo.get_by_id(document_id)
        if document is None:
            raise NotFoundError(f"document not found: {document_id}")
        stale_after = timedelta(seconds=get_settings().processing_stale_seconds)
        if document.status == DocumentStatus.PROCESSING:
            started = document.processing_started_at
            if started and datetime.now(tz=UTC) - started < stale_after:
                return document
        if document.status == DocumentStatus.READY:
            return document
        now = datetime.now(tz=UTC)
        processing = _with_status(
            document,
            DocumentStatus.PROCESSING,
            now,
            error_message=None,
            processing_started_at=now,
        )
        await self._doc_repo.save(processing)
        try:
            raw = await self._storage.get_object(document.storage_key)
            text = normalize_text(self._parsers.parse(document.mime_type, raw))
            assert_text_within_limit(text, MAX_DOCUMENT_TEXT_BYTES)
            pieces = chunk_text(
                text,
                ChunkingConfig(
                    chunk_size=CHUNK_SIZE,
                    overlap=CHUNK_OVERLAP,
                    max_chunks=MAX_CHUNK_COUNT,
                ),
            )
            if not pieces:
                raise ValidationError("document produced no chunks")
            vectors = await self._embeddings.embed_texts(pieces)
            chunks = [
                DocumentChunk(
                    id=uuid4(),
                    document_id=document.id,
                    knowledge_base_id=document.knowledge_base_id,
                    organization_id=document.organization_id,
                    chunk_index=index,
                    content=piece,
                    embedding=vector,
                    token_count=len(piece.split()),
                    created_at=now,
                    updated_at=now,
                )
                for index, (piece, vector) in enumerate(zip(pieces, vectors, strict=True))
            ]
            await self._chunk_repo.replace_for_document(document.id, chunks)
            return await self._doc_repo.save(
                _with_status(
                    document,
                    DocumentStatus.READY,
                    now,
                    error_message=None,
                    processing_started_at=None,
                ),
            )
        except Exception as exc:
            return await self._doc_repo.save(
                _with_status(
                    document,
                    DocumentStatus.FAILED,
                    now,
                    error_message=str(exc)[:2000],
                    processing_started_at=None,
                ),
            )


def _with_status(
    document: Document,
    status: DocumentStatus,
    updated_at: datetime,
    error_message: str | None,
    processing_started_at: datetime | None,
) -> Document:
    return Document(
        id=document.id,
        knowledge_base_id=document.knowledge_base_id,
        organization_id=document.organization_id,
        filename=document.filename,
        mime_type=document.mime_type,
        size_bytes=document.size_bytes,
        status=status,
        storage_key=document.storage_key,
        content_hash=document.content_hash,
        content_version=document.content_version,
        error_message=error_message,
        deleted_at=document.deleted_at,
        created_at=document.created_at,
        updated_at=updated_at,
        processing_started_at=processing_started_at,
    )
