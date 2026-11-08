import hashlib
import math

from rag_platform.application.ports.embeddings import EmbeddingProvider
from rag_platform.domain.constants import EMBEDDING_DIMENSION


class FakeEmbeddingProvider(EmbeddingProvider):
    dimension = EMBEDDING_DIMENSION

    async def embed_texts(self, texts: list[str]) -> list[list[float]]:
        return [_vector_for_text(text) for text in texts]


def _vector_for_text(text: str) -> list[float]:
    digest = hashlib.sha256(text.encode("utf-8")).digest()
    values: list[float] = []
    while len(values) < EMBEDDING_DIMENSION:
        for byte in digest:
            values.append((byte / 255.0) * 2.0 - 1.0)
            if len(values) >= EMBEDDING_DIMENSION:
                break
        digest = hashlib.sha256(digest).digest()
    norm = math.sqrt(sum(v * v for v in values)) or 1.0
    return [v / norm for v in values]
