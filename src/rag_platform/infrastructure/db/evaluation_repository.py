import json
from datetime import UTC, datetime, timedelta
from typing import Any
from uuid import UUID, uuid4

from sqlalchemy import and_, or_, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from rag_platform.application.ports.evaluations import EvaluationRepository, RecoveredEvaluation
from rag_platform.domain.entities import EvaluationRecord
from rag_platform.domain.enums import EvaluationStatus
from rag_platform.infrastructure.db.evaluation_models import EvaluationModel, EvaluationResultModel


class SqlAlchemyEvaluationRepository(EvaluationRepository):
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    def _to_record(self, row: EvaluationModel) -> EvaluationRecord:
        return EvaluationRecord(
            id=row.id,
            status=row.status,
            metrics_json=row.metrics_json,
            lease_expires_at=row.lease_expires_at,
        )

    async def create_pending(
        self,
        *,
        evaluation_id: UUID,
        knowledge_base_id: UUID,
        organization_id: UUID,
    ) -> None:
        row = EvaluationModel(
            id=evaluation_id,
            knowledge_base_id=knowledge_base_id,
            organization_id=organization_id,
            status=EvaluationStatus.PENDING,
        )
        self._session.add(row)
        await self._session.flush()

    async def mark_enqueue_failed(self, *, evaluation_id: UUID) -> None:
        row = await self._session.get(EvaluationModel, evaluation_id)
        if row is None:
            return
        row.status = EvaluationStatus.ENQUEUE_FAILED
        row.updated_at = datetime.now(tz=UTC)
        await self._session.flush()

    async def try_claim_running(self, *, evaluation_id: UUID, lease_seconds: int) -> str | None:
        token = uuid4().hex
        now = datetime.now(tz=UTC)
        expires = now + timedelta(seconds=lease_seconds)
        stmt = (
            update(EvaluationModel)
            .where(EvaluationModel.id == evaluation_id)
            .where(
                or_(
                    EvaluationModel.status.in_(
                        (
                            EvaluationStatus.PENDING,
                            EvaluationStatus.FAILED,
                            EvaluationStatus.ENQUEUE_FAILED,
                        ),
                    ),
                    and_(
                        EvaluationModel.status == EvaluationStatus.RUNNING,
                        EvaluationModel.lease_expires_at.is_not(None),
                        EvaluationModel.lease_expires_at < now,
                    ),
                ),
            )
            .values(
                status=EvaluationStatus.RUNNING,
                worker_claim_token=token,
                processing_started_at=now,
                lease_expires_at=expires,
                updated_at=now,
            )
        )
        result = await self._session.execute(stmt)
        if result.rowcount != 1:
            return None
        return token

    async def extend_lease(
        self, *, evaluation_id: UUID, claim_token: str, lease_seconds: int
    ) -> bool:
        now = datetime.now(tz=UTC)
        expires = now + timedelta(seconds=lease_seconds)
        stmt = (
            update(EvaluationModel)
            .where(EvaluationModel.id == evaluation_id)
            .where(EvaluationModel.worker_claim_token == claim_token)
            .where(EvaluationModel.status == EvaluationStatus.RUNNING)
            .values(lease_expires_at=expires, updated_at=now)
        )
        result = await self._session.execute(stmt)
        return result.rowcount == 1

    async def recover_stale_leases(self, *, batch_size: int) -> list[RecoveredEvaluation]:
        now = datetime.now(tz=UTC)
        pick = (
            select(EvaluationModel.id)
            .where(
                EvaluationModel.status == EvaluationStatus.RUNNING,
                EvaluationModel.lease_expires_at.is_not(None),
                EvaluationModel.lease_expires_at < now,
            )
            .order_by(EvaluationModel.lease_expires_at)
            .limit(batch_size)
            .with_for_update(skip_locked=True)
        )
        ids = list((await self._session.execute(pick)).scalars().all())
        if not ids:
            return []
        stmt = (
            update(EvaluationModel)
            .where(EvaluationModel.id.in_(ids))
            .where(
                EvaluationModel.status == EvaluationStatus.RUNNING,
                EvaluationModel.lease_expires_at < now,
            )
            .values(
                status=EvaluationStatus.PENDING,
                worker_claim_token=None,
                processing_started_at=None,
                lease_expires_at=None,
                updated_at=now,
            )
            .returning(
                EvaluationModel.id,
                EvaluationModel.knowledge_base_id,
                EvaluationModel.organization_id,
            )
        )
        rows = (await self._session.execute(stmt)).all()
        return [
            RecoveredEvaluation(
                evaluation_id=row[0],
                knowledge_base_id=row[1],
                organization_id=row[2],
            )
            for row in rows
        ]

    async def mark_running(self, *, evaluation_id: UUID) -> None:
        row = await self._session.get(EvaluationModel, evaluation_id)
        if row is None:
            return
        row.status = EvaluationStatus.RUNNING
        row.updated_at = datetime.now(tz=UTC)
        await self._session.flush()

    async def mark_failed(
        self, *, evaluation_id: UUID, error_message: str, claim_token: str
    ) -> bool:
        now = datetime.now(tz=UTC)
        stmt = (
            update(EvaluationModel)
            .where(EvaluationModel.id == evaluation_id)
            .where(EvaluationModel.worker_claim_token == claim_token)
            .where(EvaluationModel.status == EvaluationStatus.RUNNING)
            .values(
                status=EvaluationStatus.FAILED,
                metrics_json=json.dumps({"error": error_message}),
                worker_claim_token=None,
                lease_expires_at=None,
                processing_started_at=None,
                updated_at=now,
            )
        )
        result = await self._session.execute(stmt)
        return result.rowcount == 1

    async def add_result(
        self,
        *,
        evaluation_id: UUID,
        question: str,
        expected: str,
        answer: str,
        score: float,
        claim_token: str,
    ) -> bool:
        row = await self._session.get(EvaluationModel, evaluation_id)
        if (
            row is None
            or row.worker_claim_token != claim_token
            or row.status != EvaluationStatus.RUNNING
        ):
            return False
        self._session.add(
            EvaluationResultModel(
                evaluation_id=evaluation_id,
                question=question,
                expected=expected,
                answer=answer,
                score=score,
            ),
        )
        await self._session.flush()
        return True

    async def mark_completed(
        self,
        *,
        evaluation_id: UUID,
        metrics: dict[str, Any],
        claim_token: str,
    ) -> bool:
        now = datetime.now(tz=UTC)
        stmt = (
            update(EvaluationModel)
            .where(EvaluationModel.id == evaluation_id)
            .where(EvaluationModel.worker_claim_token == claim_token)
            .where(EvaluationModel.status == EvaluationStatus.RUNNING)
            .values(
                status=EvaluationStatus.COMPLETED,
                metrics_json=json.dumps(metrics),
                worker_claim_token=None,
                lease_expires_at=None,
                processing_started_at=None,
                updated_at=now,
            )
        )
        result = await self._session.execute(stmt)
        return result.rowcount == 1

    async def get_by_id_for_knowledge_base(
        self,
        evaluation_id: UUID,
        knowledge_base_id: UUID,
    ) -> EvaluationRecord | None:
        stmt = select(EvaluationModel).where(
            EvaluationModel.id == evaluation_id,
            EvaluationModel.knowledge_base_id == knowledge_base_id,
        )
        row = (await self._session.execute(stmt)).scalar_one_or_none()
        if row is None:
            return None
        return self._to_record(row)

    async def get_scoped(
        self,
        *,
        evaluation_id: UUID,
        knowledge_base_id: UUID,
        organization_id: UUID,
    ) -> EvaluationRecord | None:
        stmt = select(EvaluationModel).where(
            EvaluationModel.id == evaluation_id,
            EvaluationModel.knowledge_base_id == knowledge_base_id,
            EvaluationModel.organization_id == organization_id,
        )
        row = (await self._session.execute(stmt)).scalar_one_or_none()
        if row is None:
            return None
        return self._to_record(row)
