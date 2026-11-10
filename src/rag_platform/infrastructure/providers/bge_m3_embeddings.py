import asyncio
from typing import Any

from rag_platform.application.ports.embeddings import EmbeddingProvider
from rag_platform.domain.constants import EMBEDDING_DIMENSION
from rag_platform.domain.errors import ConfigurationError

_MODEL_CACHE: dict[tuple[str, str], Any] = {}


class BgeM3EmbeddingProvider(EmbeddingProvider):
    """Local bge-m3 embeddings through sentence-transformers.

    The model is loaded lazily on the first call and cached per process, so
    the HTTP layer pays the load cost once. Requires the optional extra:
    ``uv sync --extra local``.
    """

    dimension = EMBEDDING_DIMENSION

    def __init__(
        self,
        model_name: str = "BAAI/bge-m3",
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
            from sentence_transformers import SentenceTransformer
        except ImportError as exc:
            raise ConfigurationError(
                "bge-m3 embeddings require the local extra: uv sync --extra local"
            ) from exc
        model = SentenceTransformer(self._model_name, device=self._device)
        dimension = (
            model.get_embedding_dimension()
            if hasattr(model, "get_embedding_dimension")
            else model.get_sentence_embedding_dimension()
        )
        if dimension != EMBEDDING_DIMENSION:
            raise ConfigurationError(
                f"embedding model returns {dimension} dimensions, expected {EMBEDDING_DIMENSION}"
            )
        _MODEL_CACHE[key] = model
        return model

    def _encode(self, texts: list[str]) -> list[list[float]]:
        vectors = self._load().encode(
            texts,
            batch_size=self._batch_size,
            normalize_embeddings=True,
            convert_to_numpy=True,
            show_progress_bar=False,
        )
        return [vector.tolist() for vector in vectors]

    async def embed_texts(self, texts: list[str]) -> list[list[float]]:
        if not texts:
            return []
        return await asyncio.to_thread(self._encode, texts)
