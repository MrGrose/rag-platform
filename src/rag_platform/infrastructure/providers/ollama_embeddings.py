from rag_platform.application.ports.embeddings import EmbeddingProvider
from rag_platform.infrastructure.providers.fake_embeddings import FakeEmbeddingProvider


class OllamaEmbeddingProvider(EmbeddingProvider):
    def __init__(self) -> None:
        self._fallback = FakeEmbeddingProvider()
        self.dimension = self._fallback.dimension

    async def embed_texts(self, texts: list[str]) -> list[list[float]]:
        return await self._fallback.embed_texts(texts)
