from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest

from rag_platform.application.use_cases.run_evaluation import RunEvaluation
from rag_platform.domain.entities import KnowledgeBase
from rag_platform.domain.enums import EvaluationStatus
from rag_platform.domain.errors import ConflictError
from rag_platform.infrastructure.fakes.evaluation_repository import InMemoryEvaluationRepository


class _KbRepo:
    def __init__(self, kb: KnowledgeBase) -> None:
        self._kb = kb

    async def get_by_id(self, kid):
        return self._kb if kid == self._kb.id else None


@pytest.mark.asyncio
async def test_completed_is_noop() -> None:
    org = uuid4()
    kb_id = uuid4()
    ev_id = uuid4()
    now = datetime.now(tz=UTC)
    kb = KnowledgeBase(id=kb_id, organization_id=org, name="kb", created_at=now, updated_at=now)
    repo = InMemoryEvaluationRepository()
    await repo.seed(ev_id, kb_id, org, status=EvaluationStatus.COMPLETED, metrics_json="{}")
    chat = AsyncMock()
    uc = RunEvaluation(
        kb_repo=_KbRepo(kb),
        eval_repo=repo,
        chat=chat,
        dataset_items=[],
    )
    out = await uc.execute(
        evaluation_id=ev_id,
        knowledge_base_id=kb_id,
        organization_id=org,
    )
    assert out == ev_id
    chat.execute.assert_not_called()


@pytest.mark.asyncio
async def test_running_with_active_lease_is_noop() -> None:
    org = uuid4()
    kb_id = uuid4()
    ev_id = uuid4()
    now = datetime.now(tz=UTC)
    kb = KnowledgeBase(id=kb_id, organization_id=org, name="kb", created_at=now, updated_at=now)
    repo = InMemoryEvaluationRepository()
    await repo.seed(
        ev_id,
        kb_id,
        org,
        status=EvaluationStatus.RUNNING,
        metrics_json=None,
        lease_expires_at=now + timedelta(minutes=5),
    )
    chat = AsyncMock()
    uc = RunEvaluation(
        kb_repo=_KbRepo(kb),
        eval_repo=repo,
        chat=chat,
        dataset_items=[{"question": "q", "expected_contains": "a"}],
    )
    out = await uc.execute(
        evaluation_id=ev_id,
        knowledge_base_id=kb_id,
        organization_id=org,
    )
    assert out == ev_id
    chat.execute.assert_not_called()


@pytest.mark.asyncio
async def test_double_claim_only_one_runner() -> None:
    org = uuid4()
    kb_id = uuid4()
    ev_id = uuid4()
    now = datetime.now(tz=UTC)
    kb = KnowledgeBase(id=kb_id, organization_id=org, name="kb", created_at=now, updated_at=now)
    repo = InMemoryEvaluationRepository()
    await repo.create_pending(evaluation_id=ev_id, knowledge_base_id=kb_id, organization_id=org)
    chat = AsyncMock()
    chat.execute.return_value = type("R", (), {"answer": "ok", "citations": []})()
    uc = RunEvaluation(
        kb_repo=_KbRepo(kb),
        eval_repo=repo,
        chat=chat,
        dataset_items=[{"question": "q", "expected_contains": "ok"}],
    )
    first = await uc.execute(
        evaluation_id=ev_id,
        knowledge_base_id=kb_id,
        organization_id=org,
    )
    assert first == ev_id
    second = await uc.execute(
        evaluation_id=ev_id,
        knowledge_base_id=kb_id,
        organization_id=org,
    )
    assert second == ev_id
    assert chat.execute.await_count == 1


@pytest.mark.asyncio
async def test_invalid_status_raises() -> None:
    org = uuid4()
    kb_id = uuid4()
    ev_id = uuid4()
    now = datetime.now(tz=UTC)
    kb = KnowledgeBase(id=kb_id, organization_id=org, name="kb", created_at=now, updated_at=now)
    repo = InMemoryEvaluationRepository()
    await repo.seed(ev_id, kb_id, org, status="cancelled", metrics_json=None)
    uc = RunEvaluation(
        kb_repo=_KbRepo(kb),
        eval_repo=repo,
        chat=AsyncMock(),
        dataset_items=[],
    )
    with pytest.raises(ConflictError):
        await uc.execute(
            evaluation_id=ev_id,
            knowledge_base_id=kb_id,
            organization_id=org,
        )
