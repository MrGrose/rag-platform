from uuid import UUID

from rag_platform.application.ports.queries import QueryRepository
from rag_platform.domain.entities import Query, RetrievalHit
from rag_platform.domain.errors import NotFoundError


class GetQuery:
    def __init__(self, *, query_repo: QueryRepository) -> None:
        self._query_repo = query_repo

    async def execute(
        self,
        *,
        query_id: UUID,
        knowledge_base_id: UUID,
        organization_id: UUID,
    ) -> tuple[Query, list[RetrievalHit]]:
        query = await self._query_repo.get_by_id(query_id)
        if query is None or query.knowledge_base_id != knowledge_base_id:
            raise NotFoundError(f"query not found: {query_id}")
        if query.organization_id != organization_id:
            raise NotFoundError(f"query not found: {query_id}")
        hits = await self._query_repo.list_retrieval_results(query_id)
        return query, hits
