from typing import Protocol
from uuid import UUID

from rag_platform.domain.entities import Query, RetrievalHit


class QueryRepository(Protocol):
    async def create(self, query: Query) -> Query: ...

    async def get_by_id(self, query_id: UUID) -> Query | None: ...

    async def save(self, query: Query) -> Query: ...

    async def replace_retrieval_results(
        self,
        query_id: UUID,
        knowledge_base_id: UUID,
        hits: list[RetrievalHit],
    ) -> None: ...

    async def list_retrieval_results(self, query_id: UUID) -> list[RetrievalHit]: ...
