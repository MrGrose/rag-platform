from uuid import UUID

from rag_platform.application.ports.documents import DocumentRepository
from rag_platform.domain.entities import Document


class ListDocuments:
    def __init__(self, *, doc_repo: DocumentRepository) -> None:
        self._doc_repo = doc_repo

    async def execute(self, *, knowledge_base_id: UUID) -> list[Document]:
        return await self._doc_repo.list_for_knowledge_base(knowledge_base_id)
