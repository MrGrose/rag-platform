from uuid import UUID

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from rag_platform.application.ports.queries import QueryRepository
from rag_platform.domain.entities import Query, RetrievalHit
from rag_platform.domain.enums import QueryStatus
from rag_platform.infrastructure.db.models import QueryModel, RetrievalResultModel


def _to_query(row: QueryModel) -> Query:
    return Query(
        id=row.id,
        knowledge_base_id=row.knowledge_base_id,
        organization_id=row.organization_id,
        question=row.question,
        status=QueryStatus(row.status),
        answer=row.answer,
        error_message=row.error_message,
        created_at=row.created_at,
        updated_at=row.updated_at,
    )


class SqlAlchemyQueryRepository(QueryRepository):
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create(self, query: Query) -> Query:
        row = QueryModel(
            id=query.id,
            knowledge_base_id=query.knowledge_base_id,
            organization_id=query.organization_id,
            question=query.question,
            status=str(query.status),
            answer=query.answer,
            error_message=query.error_message,
        )
        self._session.add(row)
        await self._session.flush()
        await self._session.refresh(row)
        return _to_query(row)

    async def get_by_id(self, query_id: UUID) -> Query | None:
        row = await self._session.get(QueryModel, query_id)
        if row is None:
            return None
        return _to_query(row)

    async def save(self, query: Query) -> Query:
        row = await self._session.get(QueryModel, query.id)
        if row is None:
            raise ValueError(f"query not found: {query.id}")
        row.question = query.question
        row.status = str(query.status)
        row.answer = query.answer
        row.error_message = query.error_message
        await self._session.flush()
        await self._session.refresh(row)
        return _to_query(row)

    async def replace_retrieval_results(
        self,
        query_id: UUID,
        knowledge_base_id: UUID,
        hits: list[RetrievalHit],
    ) -> None:
        await self._session.execute(
            delete(RetrievalResultModel).where(RetrievalResultModel.query_id == query_id),
        )
        for hit in hits:
            self._session.add(
                RetrievalResultModel(
                    query_id=query_id,
                    knowledge_base_id=knowledge_base_id,
                    chunk_id=hit.chunk_id,
                    document_id=hit.document_id,
                    rank=hit.rank,
                    score=hit.score,
                    content=hit.content,
                ),
            )
        await self._session.flush()

    async def list_retrieval_results(self, query_id: UUID) -> list[RetrievalHit]:
        stmt = (
            select(RetrievalResultModel)
            .where(RetrievalResultModel.query_id == query_id)
            .order_by(RetrievalResultModel.rank)
        )
        result = await self._session.execute(stmt)
        hits: list[RetrievalHit] = []
        for row in result.scalars().all():
            hits.append(
                RetrievalHit(
                    chunk_id=row.chunk_id,
                    document_id=row.document_id,
                    knowledge_base_id=row.knowledge_base_id,
                    content=row.content,
                    score=row.score,
                    rank=row.rank,
                ),
            )
        return hits
