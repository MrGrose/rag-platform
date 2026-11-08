from typing import Protocol
from uuid import UUID

from rag_platform.domain.entities import DocumentChunk


class ChunkRepository(Protocol):
    async def replace_for_document(
        self,
        document_id: UUID,
        chunks: list[DocumentChunk],
    ) -> None: ...

    async def list_for_document(self, document_id: UUID) -> list[DocumentChunk]: ...

    async def delete_for_document(self, document_id: UUID) -> None: ...
