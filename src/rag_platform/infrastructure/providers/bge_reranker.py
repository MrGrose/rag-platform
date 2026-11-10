import asyncio
import math
from typing import Any

from rag_platform.application.ports.reranker import RerankerProvider
from rag_platform.domain.entities import RetrievalHit
from rag_platform.domain.errors import ConfigurationError

_MODEL_CACHE: dict[tuple[str, str], Any] = {}


def _sigmoid(value: float) -> float:
    if value >= 0:
        return 1.0 / (1.0 + math.exp(-value))
    exp = math.exp(value)
    return exp / (1.0 + exp)


class BgeRerankerProvider(RerankerProvider):
    """Cross-encoder reranker over bge-reranker-v2-m3.

    Scores are squashed with a sigmoid so callers can compare them with a
    relevance threshold. Requires the optional extra: ``uv sync --extra local``.
    """

    def __init__(
        self,
        model_name: str = "BAAI/bge-reranker-v2-m3",
        device: str = "cpu",
        batch_size: int = 16,
    ) -> None:
        self._model_name = model_name
        self._device = device
        self._batch_size = batch_size

    def _load(self) -> Any:
        key = (self._model_name, self._device)
        model = _MODEL_CACHE.get(key)
        if model is not None:
            return model
        try:
            from sentence_transformers import CrossEncoder
        except ImportError as exc:
            raise ConfigurationError(
                "bge reranker requires the local extra: uv sync --extra local"
            ) from exc
        model = CrossEncoder(self._model_name, device=self._device)
        _MODEL_CACHE[key] = model
        return model

    def _predict(self, question: str, contents: list[str]) -> list[float]:
        scores = self._load().predict(
            [(question, content) for content in contents],
            batch_size=self._batch_size,
            show_progress_bar=False,
        )
        return [float(score) for score in scores]

    async def rerank(
        self,
        question: str,
        hits: list[RetrievalHit],
        limit: int,
    ) -> list[RetrievalHit]:
        if not hits:
            return []
        scores = await asyncio.to_thread(self._predict, question, [hit.content for hit in hits])
        order = sorted(range(len(hits)), key=lambda index: scores[index], reverse=True)[:limit]
        reranked: list[RetrievalHit] = []
        for rank, index in enumerate(order, start=1):
            hit = hits[index]
            reranked.append(
                RetrievalHit(
                    chunk_id=hit.chunk_id,
                    document_id=hit.document_id,
                    knowledge_base_id=hit.knowledge_base_id,
                    content=hit.content,
                    score=_sigmoid(scores[index]),
                    rank=rank,
                ),
            )
        return reranked
