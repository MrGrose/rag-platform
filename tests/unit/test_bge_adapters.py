import sys
import types
from uuid import uuid4

import pytest

from rag_platform.domain.entities import RetrievalHit
from rag_platform.infrastructure.providers.bge_m3_embeddings import BgeM3EmbeddingProvider
from rag_platform.infrastructure.providers.bge_reranker import BgeRerankerProvider


class _Vector(list):
    def tolist(self) -> list[float]:
        return list(self)


class _FakeSentenceTransformer:
    instances: list["_FakeSentenceTransformer"] = []

    def __init__(self, name: str, device: str = "cpu") -> None:
        self.name = name
        self.device = device
        _FakeSentenceTransformer.instances.append(self)

    def get_sentence_embedding_dimension(self) -> int:
        return 1024

    def encode(self, texts, **_kwargs):
        return [_Vector([0.01] * 1024) for _ in texts]


class _FakeCrossEncoder:
    def __init__(self, name: str, device: str = "cpu") -> None:
        self.name = name
        self.device = device

    def predict(self, pairs, **_kwargs):
        return [0.0, 4.0][: len(pairs)]


@pytest.fixture
def fake_sentence_transformers(monkeypatch):
    module = types.ModuleType("sentence_transformers")
    module.SentenceTransformer = _FakeSentenceTransformer
    module.CrossEncoder = _FakeCrossEncoder
    monkeypatch.setitem(sys.modules, "sentence_transformers", module)
    _FakeSentenceTransformer.instances.clear()
    return module


def _hit(score: float = 0.0) -> RetrievalHit:
    return RetrievalHit(
        chunk_id=uuid4(),
        document_id=uuid4(),
        knowledge_base_id=uuid4(),
        content="chunk",
        score=score,
        rank=1,
    )


async def test_embeddings_use_bge_model(fake_sentence_transformers) -> None:
    provider = BgeM3EmbeddingProvider(model_name="BAAI/bge-m3", device="cpu")
    vectors = await provider.embed_texts(["one", "two"])
    assert len(vectors) == 2
    assert len(vectors[0]) == 1024
    assert _FakeSentenceTransformer.instances[0].name == "BAAI/bge-m3"


async def test_reranker_orders_by_score(fake_sentence_transformers) -> None:
    hits = [_hit(0.9), _hit(0.1)]
    provider = BgeRerankerProvider(model_name="BAAI/bge-reranker-v2-m3", device="cpu")
    reranked = await provider.rerank("question", hits, limit=2)
    assert [hit.chunk_id for hit in reranked] == [hits[1].chunk_id, hits[0].chunk_id]
    assert reranked[0].score > 0.9
    assert reranked[1].score == pytest.approx(0.5)


async def test_reranker_empty_input(fake_sentence_transformers) -> None:
    provider = BgeRerankerProvider()
    assert await provider.rerank("question", [], limit=5) == []
