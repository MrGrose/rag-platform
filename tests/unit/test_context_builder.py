from uuid import uuid4

from rag_platform.application.context.builder import build_context, estimate_tokens
from rag_platform.domain.entities import RetrievalHit


def test_build_context_respects_token_budget() -> None:
    d = uuid4()
    kb = uuid4()
    hits = [
        RetrievalHit(
            chunk_id=uuid4(),
            document_id=d,
            knowledge_base_id=kb,
            content="word " * 200,
            score=1.0,
            rank=1,
        ),
        RetrievalHit(
            chunk_id=uuid4(),
            document_id=d,
            knowledge_base_id=kb,
            content="more " * 200,
            score=0.9,
            rank=2,
        ),
    ]
    _, selected = build_context(hits, estimate_tokens(hits[0].content) + 5)
    assert len(selected) == 1
