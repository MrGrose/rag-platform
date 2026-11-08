from uuid import UUID

from rag_platform.application.ports.documents import DocumentRepository
from rag_platform.domain.entities import Document
from rag_platform.domain.errors import NotFoundError


class GetDocument:
    def __init__(self, *, doc_repo: DocumentRepository) -> None:
        self._doc_repo = doc_repo

    async def execute(self, *, document_id: UUID, knowledge_base_id: UUID) -> Document:
        document = await self._doc_repo.get_by_id_for_kb(document_id, knowledge_base_id)
        if document is None:
            raise NotFoundError(f"document not found: {document_id}")
        return document
