from collections.abc import Awaitable, Callable
from uuid import UUID

from rag_platform.application.ports.documents import DocumentRepository
from rag_platform.config import get_settings

EnqueueProcessDocument = Callable[[UUID, UUID, UUID], Awaitable[None]]


class RequeueStaleDocuments:
    def __init__(
        self,
        *,
        doc_repo: DocumentRepository,
        enqueue: EnqueueProcessDocument,
    ) -> None:
        self._doc_repo = doc_repo
        self._enqueue = enqueue

    async def execute(self) -> int:
        stale_seconds = get_settings().processing_stale_seconds
        candidates = await self._doc_repo.list_stale_for_requeue(stale_seconds)
        for document in candidates:
            await self._enqueue(
                document.id,
                document.knowledge_base_id,
                document.organization_id,
            )
        return len(candidates)
