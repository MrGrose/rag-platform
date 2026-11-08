from rag_platform.application.ports.reranker import RerankerProvider
from rag_platform.domain.entities import RetrievalHit


class FakeRerankerProvider(RerankerProvider):
    async def rerank(
        self,
        question: str,
        hits: list[RetrievalHit],
        limit: int,
    ) -> list[RetrievalHit]:
        _ = question
        ordered = sorted(hits, key=lambda hit: hit.score, reverse=True)[:limit]
        reranked: list[RetrievalHit] = []
        for index, hit in enumerate(ordered, start=1):
            reranked.append(
                RetrievalHit(
                    chunk_id=hit.chunk_id,
                    document_id=hit.document_id,
                    knowledge_base_id=hit.knowledge_base_id,
                    content=hit.content,
                    score=hit.score,
                    rank=index,
                ),
            )
        return reranked
