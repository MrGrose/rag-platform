from typing import Protocol
from uuid import UUID

from rag_platform.domain.entities import RetrievalHit


class RetrievalEngine(Protocol):
    async def retrieve(
        self,
        *,
        organization_id: UUID,
        knowledge_base_id: UUID,
        question: str,
        limit: int,
    ) -> list[RetrievalHit]: ...
