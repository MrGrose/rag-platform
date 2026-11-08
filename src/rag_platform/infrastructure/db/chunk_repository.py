from uuid import UUID

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from rag_platform.application.ports.chunks import ChunkRepository
from rag_platform.domain.entities import DocumentChunk
from rag_platform.infrastructure.db.models import DocumentChunkModel


def _to_chunk(row: DocumentChunkModel) -> DocumentChunk:
    return DocumentChunk(
        id=row.id,
        document_id=row.document_id,
        knowledge_base_id=row.knowledge_base_id,
        organization_id=row.organization_id,
        chunk_index=row.chunk_index,
        content=row.content,
        embedding=list(row.embedding),
        token_count=row.token_count,
        created_at=row.created_at,
        updated_at=row.updated_at,
    )


class SqlAlchemyChunkRepository(ChunkRepository):
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def replace_for_document(
        self,
        document_id: UUID,
        chunks: list[DocumentChunk],
    ) -> None:
        await self.delete_for_document(document_id)
        for chunk in chunks:
            row = DocumentChunkModel(
                id=chunk.id,
                document_id=chunk.document_id,
                knowledge_base_id=chunk.knowledge_base_id,
                organization_id=chunk.organization_id,
                chunk_index=chunk.chunk_index,
                content=chunk.content,
                embedding=chunk.embedding,
                token_count=chunk.token_count,
            )
            self._session.add(row)
        await self._session.flush()

    async def list_for_document(self, document_id: UUID) -> list[DocumentChunk]:
        stmt = (
            select(DocumentChunkModel)
            .where(DocumentChunkModel.document_id == document_id)
            .order_by(DocumentChunkModel.chunk_index)
        )
        result = await self._session.execute(stmt)
        return [_to_chunk(row) for row in result.scalars().all()]

    async def delete_for_document(self, document_id: UUID) -> None:
        stmt = delete(DocumentChunkModel).where(DocumentChunkModel.document_id == document_id)
        await self._session.execute(stmt)
        await self._session.flush()
