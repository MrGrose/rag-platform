from typing import Protocol

from rag_platform.domain.entities import RetrievalHit


class RerankerProvider(Protocol):
    async def rerank(
        self,
        question: str,
        hits: list[RetrievalHit],
        limit: int,
    ) -> list[RetrievalHit]: ...
