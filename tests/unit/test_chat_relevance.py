from uuid import uuid4

from rag_platform.application.use_cases.chat import has_relevant_context
from rag_platform.domain.entities import RetrievalHit


def _hit(score: float) -> RetrievalHit:
    return RetrievalHit(
        chunk_id=uuid4(),
        document_id=uuid4(),
        knowledge_base_id=uuid4(),
        content="chunk",
        score=score,
        rank=1,
    )


def test_empty_hits_are_not_relevant() -> None:
    assert has_relevant_context([], 0.2) is False


def test_score_below_threshold_is_not_relevant() -> None:
    assert has_relevant_context([_hit(0.1)], 0.2) is False


def test_score_at_threshold_is_relevant() -> None:
    assert has_relevant_context([_hit(0.2)], 0.2) is True
