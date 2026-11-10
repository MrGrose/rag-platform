from dataclasses import replace
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from rag_platform.application.ports.embeddings import EmbeddingProvider
from rag_platform.application.ports.retrieval import RetrievalEngine
from rag_platform.application.retrieval.hybrid import fuse_hits
from rag_platform.application.retrieval.preprocess import preprocess_question
from rag_platform.domain.entities import RetrievalHit
from rag_platform.infrastructure.db.models import DocumentChunkModel


class PgHybridRetrievalEngine(RetrievalEngine):
    def __init__(
        self,
        session: AsyncSession,
        embeddings: EmbeddingProvider,
        mode: str = "hybrid",
    ) -> None:
        self._session = session
        self._embeddings = embeddings
        self._mode = mode.strip().lower()
        if self._mode not in {"vector", "hybrid"}:
            raise ValueError(f"unsupported retrieval mode: {mode}")

    async def retrieve(
        self,
        *,
        organization_id: UUID,
        knowledge_base_id: UUID,
        question: str,
        limit: int,
    ) -> list[RetrievalHit]:
        normalized = preprocess_question(question)
        query_vec = (await self._embeddings.embed_texts([normalized]))[0]
        scope = (
            DocumentChunkModel.knowledge_base_id == knowledge_base_id,
            DocumentChunkModel.organization_id == organization_id,
        )
        vector_stmt = (
            select(
                DocumentChunkModel,
                DocumentChunkModel.embedding.cosine_distance(query_vec).label("distance"),
            )
            .where(*scope)
            .order_by("distance")
            .limit(limit)
        )
        vector_rows = await self._session.execute(vector_stmt)
        vector_hits: list[tuple[UUID, UUID, UUID, str, float]] = []
        pages: dict[UUID, int | None] = {}
        for chunk, distance in vector_rows.all():
            pages[chunk.id] = chunk.page
            score = 1.0 / (1.0 + float(distance))
            vector_hits.append(
                (chunk.id, chunk.document_id, chunk.knowledge_base_id, chunk.content, score),
            )

        if self._mode == "vector":
            fused = fuse_hits(vector_hits, [], limit)
            return [replace(hit, page=pages.get(hit.chunk_id)) for hit in fused]

        ts_query = func.plainto_tsquery("english", normalized)
        ts_vector = func.to_tsvector("english", DocumentChunkModel.content)
        fts_stmt = (
            select(
                DocumentChunkModel,
                func.ts_rank_cd(ts_vector, ts_query).label("rank"),
            )
            .where(*scope)
            .where(ts_vector.op("@@")(ts_query))
            .order_by(func.ts_rank_cd(ts_vector, ts_query).desc())
            .limit(limit)
        )
        fts_rows = await self._session.execute(fts_stmt)
        lexical_hits: list[tuple[UUID, UUID, UUID, str, float]] = []
        for chunk, rank in fts_rows.all():
            pages[chunk.id] = chunk.page
            lexical_hits.append(
                (chunk.id, chunk.document_id, chunk.knowledge_base_id, chunk.content, float(rank)),
            )
        fused = fuse_hits(vector_hits, lexical_hits, limit)
        return [replace(hit, page=pages.get(hit.chunk_id)) for hit in fused]


def hit_from_row(
    chunk_id: UUID,
    document_id: UUID,
    knowledge_base_id: UUID,
    content: str,
    score: float,
    rank: int,
) -> RetrievalHit:
    return RetrievalHit(
        chunk_id=chunk_id,
        document_id=document_id,
        knowledge_base_id=knowledge_base_id,
        content=content,
        score=score,
        rank=rank,
    )
