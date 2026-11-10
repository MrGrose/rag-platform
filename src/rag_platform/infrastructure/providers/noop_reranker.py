from rag_platform.application.ports.reranker import RerankerProvider
from rag_platform.domain.entities import RetrievalHit


class NoopRerankerProvider(RerankerProvider):
    """Keeps retrieval order and only truncates, for ablation runs."""

    async def rerank(
        self,
        question: str,
        hits: list[RetrievalHit],
        limit: int,
    ) -> list[RetrievalHit]:
        _ = question
        return hits[:limit]
