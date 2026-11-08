from typing import Protocol
from uuid import UUID

from rag_platform.domain.entities import Document


class DocumentRepository(Protocol):
    async def create(self, document: Document) -> Document: ...

    async def get_by_id(self, document_id: UUID) -> Document | None: ...

    async def get_by_id_for_kb(
        self,
        document_id: UUID,
        knowledge_base_id: UUID,
    ) -> Document | None: ...

    async def list_for_knowledge_base(self, knowledge_base_id: UUID) -> list[Document]: ...

    async def get_by_content_hash(
        self,
        knowledge_base_id: UUID,
        content_hash: str,
    ) -> Document | None: ...

    async def save(self, document: Document) -> Document: ...

    async def list_stale_for_requeue(self, stale_seconds: int) -> list[Document]: ...
