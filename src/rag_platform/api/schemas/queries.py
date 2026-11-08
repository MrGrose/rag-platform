from datetime import datetime
from uuid import UUID

from pydantic import BaseModel

from rag_platform.domain.entities import Query, RetrievalHit


class RetrievalHitResponse(BaseModel):
    chunk_id: UUID
    document_id: UUID
    score: float
    rank: int
    content: str


class QueryResponse(BaseModel):
    id: UUID
    knowledge_base_id: UUID
    question: str
    status: str
    answer: str | None
    created_at: datetime
    retrieval_results: list[RetrievalHitResponse]

    @classmethod
    def from_entity(cls, query: Query, hits: list[RetrievalHit]) -> "QueryResponse":
        return cls(
            id=query.id,
            knowledge_base_id=query.knowledge_base_id,
            question=query.question,
            status=str(query.status),
            answer=query.answer,
            created_at=query.created_at,
            retrieval_results=[
                RetrievalHitResponse(
                    chunk_id=h.chunk_id,
                    document_id=h.document_id,
                    score=h.score,
                    rank=h.rank,
                    content=h.content,
                )
                for h in hits
            ],
        )
