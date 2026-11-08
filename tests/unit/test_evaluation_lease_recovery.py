from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest

from rag_platform.application.use_cases.recover_stale_evaluations import RecoverStaleEvaluations
from rag_platform.domain.enums import EvaluationStatus
from rag_platform.infrastructure.fakes.evaluation_repository import InMemoryEvaluationRepository


@pytest.mark.asyncio
async def test_stale_running_is_recovered_and_requeued() -> None:
    org = uuid4()
    kb_id = uuid4()
    ev_id = uuid4()
    repo = InMemoryEvaluationRepository()
    await repo.seed(
        ev_id,
        kb_id,
        org,
        status=EvaluationStatus.RUNNING,
        metrics_json=None,
        lease_expires_at=datetime.now(tz=UTC) - timedelta(seconds=30),
        claim_token="stale-token",
    )
    enqueue = AsyncMock()
    count = await RecoverStaleEvaluations(eval_repo=repo, enqueue=enqueue).execute()
    assert count == 1
    enqueue.assert_awaited_once()
    row = await repo.get_scoped(
        evaluation_id=ev_id,
        knowledge_base_id=kb_id,
        organization_id=org,
    )
    assert row is not None
    assert row.status == EvaluationStatus.PENDING


@pytest.mark.asyncio
async def test_active_running_lease_not_recovered() -> None:
    org = uuid4()
    kb_id = uuid4()
    ev_id = uuid4()
    repo = InMemoryEvaluationRepository()
    await repo.seed(
        ev_id,
        kb_id,
        org,
        status=EvaluationStatus.RUNNING,
        metrics_json=None,
        lease_expires_at=datetime.now(tz=UTC) + timedelta(minutes=5),
        claim_token="active",
    )
    enqueue = AsyncMock()
    count = await RecoverStaleEvaluations(eval_repo=repo, enqueue=enqueue).execute()
    assert count == 0
    enqueue.assert_not_called()


@pytest.mark.asyncio
async def test_wrong_claim_token_cannot_complete() -> None:
    org = uuid4()
    kb_id = uuid4()
    ev_id = uuid4()
    repo = InMemoryEvaluationRepository()
    await repo.seed(
        ev_id,
        kb_id,
        org,
        status=EvaluationStatus.RUNNING,
        metrics_json=None,
        lease_expires_at=datetime.now(tz=UTC) + timedelta(minutes=5),
        claim_token="owner",
    )
    ok = await repo.mark_completed(
        evaluation_id=ev_id,
        metrics={"accuracy": 1.0},
        claim_token="intruder",
    )
    assert ok is False
    row = await repo.get_scoped(
        evaluation_id=ev_id,
        knowledge_base_id=kb_id,
        organization_id=org,
    )
    assert row is not None
    assert row.status == EvaluationStatus.RUNNING
