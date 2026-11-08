from datetime import UTC, datetime
from uuid import uuid4

import pytest

from rag_platform.application.use_cases.start_evaluation import StartEvaluation
from rag_platform.domain.entities import KnowledgeBase
from rag_platform.domain.enums import EvaluationStatus
from rag_platform.infrastructure.fakes.evaluation_repository import InMemoryEvaluationRepository
from rag_platform.infrastructure.fakes.outbox_repository import InMemoryOutboxRepository


class _KbRepo:
    def __init__(self, kb: KnowledgeBase) -> None:
        self._kb = kb

    async def get_by_id(self, kid):
        return self._kb if kid == self._kb.id else None


@pytest.mark.asyncio
async def test_start_evaluation_returns_id_and_pending() -> None:
    org = uuid4()
    kb_id = uuid4()
    now = datetime.now(tz=UTC)
    kb = KnowledgeBase(id=kb_id, organization_id=org, name="main", created_at=now, updated_at=now)
    eval_repo = InMemoryEvaluationRepository()
    outbox = InMemoryOutboxRepository()
    uc = StartEvaluation(kb_repo=_KbRepo(kb), eval_repo=eval_repo, outbox_repo=outbox)
    record = await uc.execute(knowledge_base_id=kb_id, organization_id=org)
    assert record.status == EvaluationStatus.PENDING
    assert len(outbox.events) == 1
    assert outbox.events[0]["aggregate_id"] == record.id
