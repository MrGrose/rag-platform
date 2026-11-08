import asyncio
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest

from rag_platform.application.use_cases.recover_stale_evaluations import RecoverStaleEvaluations
from rag_platform.domain.enums import EvaluationStatus
from rag_platform.infrastructure.db.evaluation_repository import SqlAlchemyEvaluationRepository
from rag_platform.infrastructure.db.repositories import (
    SqlAlchemyKnowledgeBaseRepository,
    SqlAlchemyOrganizationRepository,
)
from rag_platform.infrastructure.db.session import session_scope

pytestmark = pytest.mark.integration


@pytest.mark.asyncio
async def test_stale_running_recovered_atomically() -> None:
    ev_id = None
    kb_id = None
    org_id = None
    async with session_scope() as session:
        org = await SqlAlchemyOrganizationRepository(session).create(f"lease-{uuid4().hex[:6]}")
        kb = await SqlAlchemyKnowledgeBaseRepository(session).create(org.id, "kb")
        ev_id = uuid4()
        repo = SqlAlchemyEvaluationRepository(session)
        await repo.create_pending(
            evaluation_id=ev_id,
            knowledge_base_id=kb.id,
            organization_id=org.id,
        )
        token = await repo.try_claim_running(evaluation_id=ev_id, lease_seconds=1)
        assert token
        kb_id, org_id = kb.id, org.id
        row = await repo.get_scoped(
            evaluation_id=ev_id,
            knowledge_base_id=kb_id,
            organization_id=org_id,
        )
        assert row and row.status == EvaluationStatus.RUNNING

    await asyncio.sleep(1.2)

    enqueue = AsyncMock()
    async with session_scope() as session:
        count = await RecoverStaleEvaluations(
            eval_repo=SqlAlchemyEvaluationRepository(session),
            enqueue=enqueue,
        ).execute()
        assert count >= 1

    async with session_scope() as session:
        row = await SqlAlchemyEvaluationRepository(session).get_scoped(
            evaluation_id=ev_id,
            knowledge_base_id=kb_id,
            organization_id=org_id,
        )
        assert row is not None
        assert row.status == EvaluationStatus.PENDING
    assert enqueue.await_count >= 1


@pytest.mark.asyncio
async def test_concurrent_recovery_skip_locked() -> None:
    ids = []
    async with session_scope() as session:
        org = await SqlAlchemyOrganizationRepository(session).create(f"lease2-{uuid4().hex[:6]}")
        kb = await SqlAlchemyKnowledgeBaseRepository(session).create(org.id, "kb")
        repo = SqlAlchemyEvaluationRepository(session)
        for _ in range(2):
            ev = uuid4()
            await repo.create_pending(
                evaluation_id=ev,
                knowledge_base_id=kb.id,
                organization_id=org.id,
            )
            await repo.try_claim_running(evaluation_id=ev, lease_seconds=1)
            ids.append(ev)

    await asyncio.sleep(1.2)

    async def recover():
        async with session_scope() as session:
            return await RecoverStaleEvaluations(
                eval_repo=SqlAlchemyEvaluationRepository(session),
                enqueue=AsyncMock(),
            ).execute()

    c1, c2 = await asyncio.gather(recover(), recover())
    assert c1 + c2 >= 2


@pytest.mark.asyncio
async def test_stale_worker_cannot_complete_after_lease_lost() -> None:
    ev_id = None
    kb_id = None
    org_id = None
    stale_token = "stale-token"
    async with session_scope() as session:
        org = await SqlAlchemyOrganizationRepository(session).create(f"lease3-{uuid4().hex[:6]}")
        kb = await SqlAlchemyKnowledgeBaseRepository(session).create(org.id, "kb")
        ev_id = uuid4()
        repo = SqlAlchemyEvaluationRepository(session)
        await repo.create_pending(
            evaluation_id=ev_id,
            knowledge_base_id=kb.id,
            organization_id=org.id,
        )
        new_token = await repo.try_claim_running(evaluation_id=ev_id, lease_seconds=30)
        assert new_token
        kb_id, org_id = kb.id, org.id

    ok = False
    async with session_scope() as session:
        ok = await SqlAlchemyEvaluationRepository(session).mark_completed(
            evaluation_id=ev_id,
            metrics={"accuracy": 1.0},
            claim_token=stale_token,
        )
    assert ok is False

    async with session_scope() as session:
        row = await SqlAlchemyEvaluationRepository(session).get_scoped(
            evaluation_id=ev_id,
            knowledge_base_id=kb_id,
            organization_id=org_id,
        )
        assert row is not None
        assert row.status == EvaluationStatus.RUNNING
