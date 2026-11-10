from rag_platform.application.ports.embeddings import EmbeddingProvider
from rag_platform.infrastructure.cache.redis_cache import (
    cache_get,
    cache_set,
    deserialize_vectors,
    hash_embedding_inputs,
    serialize_vectors,
)


class CachedEmbeddingProvider(EmbeddingProvider):
    def __init__(self, inner: EmbeddingProvider, kb_version: str) -> None:
        self._inner = inner
        self._kb_version = kb_version
        self.dimension = inner.dimension
        model = getattr(inner, "model_name", "")
        self._namespace = f"{type(inner).__name__}:{inner.dimension}:{model}:{kb_version}"

    async def embed_texts(self, texts: list[str]) -> list[list[float]]:
        digest = hash_embedding_inputs(texts)
        key = f"{self._namespace}:{digest}"
        cached = await cache_get("emb", key)
        if cached is not None:
            return deserialize_vectors(cached)
        vectors = await self._inner.embed_texts(texts)
        await cache_set("emb", key, serialize_vectors(vectors), ttl_seconds=3600)
        return vectors
