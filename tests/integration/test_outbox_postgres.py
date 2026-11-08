import asyncio
from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock, patch
from uuid import uuid4

import pytest
from sqlalchemy import delete, select

from rag_platform.application.use_cases.start_evaluation import StartEvaluation
from rag_platform.domain.enums import EvaluationStatus
from rag_platform.infrastructure.db.evaluation_repository import SqlAlchemyEvaluationRepository
from rag_platform.infrastructure.db.outbox_models import OutboxEventModel
from rag_platform.infrastructure.db.outbox_repository import SqlAlchemyOutboxRepository
from rag_platform.infrastructure.db.repositories import (
    SqlAlchemyKnowledgeBaseRepository,
    SqlAlchemyOrganizationRepository,
)
from rag_platform.infrastructure.db.session import get_session_factory, session_scope

pytestmark = pytest.mark.integration


@pytest.fixture(autouse=True)
async def outbox_release_stale_locks():
    async with session_scope() as session:
        await session.execute(delete(OutboxEventModel))
        await session.commit()
    async with session_scope() as session:
        repo = SqlAlchemyOutboxRepository(session)
        now = datetime.now(tz=UTC)
        await repo.release_stale_processing(now=now, lease_seconds=0)
        await session.commit()
    yield


async def _seed_org_kb(session):
    org = await SqlAlchemyOrganizationRepository(session).create(f"outbox-test-{uuid4().hex[:8]}")
    kb = await SqlAlchemyKnowledgeBaseRepository(session).create(org.id, "kb")
    return org, kb


@pytest.mark.asyncio
async def test_evaluation_and_outbox_same_transaction_commits() -> None:
    ev_id = None
    kb_id = None
    org_id = None
    async with session_scope() as session:
        org, kb = await _seed_org_kb(session)
        kb_id, org_id = kb.id, org.id
        uc = StartEvaluation(
            kb_repo=SqlAlchemyKnowledgeBaseRepository(session),
            eval_repo=SqlAlchemyEvaluationRepository(session),
            outbox_repo=SqlAlchemyOutboxRepository(session),
        )
        record = await uc.execute(knowledge_base_id=kb.id, organization_id=org.id)
        ev_id = record.id

    async with session_scope() as session:
        row = await SqlAlchemyEvaluationRepository(session).get_scoped(
            evaluation_id=ev_id,
            knowledge_base_id=kb_id,
            organization_id=org_id,
        )
        assert row is not None
        assert row.status == EvaluationStatus.PENDING
        out_row = (
            await session.execute(
                select(OutboxEventModel).where(OutboxEventModel.aggregate_id == ev_id),
            )
        ).scalar_one_or_none()
        assert out_row is not None
        assert out_row.status == "pending"


@pytest.mark.asyncio
async def test_evaluation_and_outbox_rollback() -> None:
    ev_id = None
    kb_id = None
    org_id = None
    factory = get_session_factory()
    session = factory()
    try:
        org, kb = await _seed_org_kb(session)
        org_id, kb_id = org.id, kb.id
        uc = StartEvaluation(
            kb_repo=SqlAlchemyKnowledgeBaseRepository(session),
            eval_repo=SqlAlchemyEvaluationRepository(session),
            outbox_repo=SqlAlchemyOutboxRepository(session),
        )
        record = await uc.execute(knowledge_base_id=kb.id, organization_id=org.id)
        ev_id = record.id
        raise RuntimeError("force rollback")
    except RuntimeError:
        await session.rollback()
    finally:
        await session.close()

    async with session_scope() as session:
        row = await SqlAlchemyEvaluationRepository(session).get_scoped(
            evaluation_id=ev_id,
            knowledge_base_id=kb_id,
            organization_id=org_id,
        )
        assert row is None


@pytest.mark.asyncio
async def test_outbox_skip_locked_single_claim_per_event() -> None:
    async with session_scope() as session:
        org, _ = await _seed_org_kb(session)
        repo = SqlAlchemyOutboxRepository(session)
        await repo.append(
            event_type="evaluation.run",
            aggregate_id=uuid4(),
            organization_id=org.id,
            payload={"evaluation_id": str(uuid4())},
        )
        await repo.append(
            event_type="evaluation.run",
            aggregate_id=uuid4(),
            organization_id=org.id,
            payload={"evaluation_id": str(uuid4())},
        )
        await session.commit()

    async def claim(token: str):
        async with session_scope() as session:
            repo = SqlAlchemyOutboxRepository(session)
            now = datetime.now(tz=UTC)
            rows = await repo.claim_batch(limit=1, lock_token=token, locked_at=now, now=now)
            ids = [r.id for r in rows]
            await session.commit()
            return ids

    id_a, id_b = await asyncio.gather(claim("tok-a"), claim("tok-b"))
    assert len(id_a) == 1 and len(id_b) == 1
    assert id_a[0] != id_b[0]


@pytest.mark.asyncio
async def test_outbox_stale_processing_lock_released() -> None:
    event_id = None
    async with session_scope() as session:
        org, _ = await _seed_org_kb(session)
        repo = SqlAlchemyOutboxRepository(session)
        now = datetime.now(tz=UTC)
        event_id = await repo.append(
            event_type="evaluation.run",
            aggregate_id=uuid4(),
            organization_id=org.id,
            payload={"evaluation_id": str(uuid4())},
        )
        await session.execute(
            select(OutboxEventModel).where(OutboxEventModel.id == event_id).with_for_update()
        )
        row = (
            await session.execute(select(OutboxEventModel).where(OutboxEventModel.id == event_id))
        ).scalar_one()
        row.status = "processing"
        row.lock_token = "stale"
        row.locked_at = now - timedelta(minutes=5)
        await session.flush()
        await repo.release_stale_processing(now=now, lease_seconds=60)
        refreshed = (
            await session.execute(select(OutboxEventModel).where(OutboxEventModel.id == event_id))
        ).scalar_one()
        assert refreshed.status == "pending"
        assert refreshed.lock_token is None


@pytest.mark.asyncio
async def test_outbox_enqueue_failure_increments_attempts() -> None:
    from rag_platform.workers import outbox_dispatcher

    event_id = None
    async with session_scope() as session:
        org, _ = await _seed_org_kb(session)
        repo = SqlAlchemyOutboxRepository(session)
        now = datetime.now(tz=UTC)
        event_id = await repo.append(
            event_type="evaluation.run",
            aggregate_id=uuid4(),
            organization_id=org.id,
            payload={
                "evaluation_id": str(uuid4()),
                "knowledge_base_id": str(uuid4()),
                "organization_id": str(org.id),
            },
        )
        await repo.claim_batch(limit=1, lock_token="fail", locked_at=now, now=now)
        await session.commit()

    with patch(
        "rag_platform.workers.outbox_dispatcher.enqueue_run_evaluation",
        new=AsyncMock(side_effect=ConnectionError("redis down")),
    ):
        await outbox_dispatcher.dispatch_outbox_events({})

    async with session_scope() as session:
        row = (
            await session.execute(select(OutboxEventModel).where(OutboxEventModel.id == event_id))
        ).scalar_one()
        assert row.status == "pending"
        assert row.attempts == 1


@pytest.mark.asyncio
async def test_published_outbox_not_reclaimed() -> None:
    async with session_scope() as session:
        org, _ = await _seed_org_kb(session)
        repo = SqlAlchemyOutboxRepository(session)
        now = datetime.now(tz=UTC)
        event_id = await repo.append(
            event_type="evaluation.run",
            aggregate_id=uuid4(),
            organization_id=org.id,
            payload={"evaluation_id": str(uuid4())},
        )
        row = (
            await session.execute(select(OutboxEventModel).where(OutboxEventModel.id == event_id))
        ).scalar_one()
        row.status = "processing"
        row.lock_token = "pub"
        row.locked_at = now
        await session.flush()
        await repo.mark_published(event_id, now)
        pending = await repo.claim_batch(limit=50, lock_token="again", locked_at=now, now=now)
        assert all(r.id != event_id for r in pending)
