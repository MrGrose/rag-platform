from datetime import UTC, datetime, timedelta
from typing import Any
from uuid import UUID, uuid4

from rag_platform.application.ports.evaluations import RecoveredEvaluation
from rag_platform.domain.entities import EvaluationRecord
from rag_platform.domain.enums import EvaluationStatus


class InMemoryEvaluationRepository:
    def __init__(self) -> None:
        self._rows: dict[UUID, dict[str, object]] = {}

    async def seed(
        self,
        evaluation_id: UUID,
        knowledge_base_id: UUID,
        organization_id: UUID,
        *,
        status: str,
        metrics_json: str | None,
        lease_expires_at: datetime | None = None,
        claim_token: str | None = None,
    ) -> None:
        self._rows[evaluation_id] = {
            "kb": knowledge_base_id,
            "org": organization_id,
            "status": status,
            "metrics": metrics_json,
            "lease": lease_expires_at,
            "token": claim_token,
        }

    def _rec(self, evaluation_id: UUID) -> EvaluationRecord | None:
        row = self._rows.get(evaluation_id)
        if row is None:
            return None
        return EvaluationRecord(
            id=evaluation_id,
            status=str(row["status"]),
            metrics_json=row["metrics"],  # type: ignore[arg-type]
            lease_expires_at=row["lease"],  # type: ignore[arg-type]
        )

    async def create_pending(
        self,
        *,
        evaluation_id: UUID,
        knowledge_base_id: UUID,
        organization_id: UUID,
    ) -> None:
        self._rows[evaluation_id] = {
            "kb": knowledge_base_id,
            "org": organization_id,
            "status": EvaluationStatus.PENDING,
            "metrics": None,
            "lease": None,
            "token": None,
        }

    async def mark_enqueue_failed(self, *, evaluation_id: UUID) -> None:
        row = self._rows.get(evaluation_id)
        if row:
            row["status"] = EvaluationStatus.ENQUEUE_FAILED

    async def try_claim_running(self, *, evaluation_id: UUID, lease_seconds: int) -> str | None:
        row = self._rows.get(evaluation_id)
        if row is None:
            return None
        now = datetime.now(tz=UTC)
        status = str(row["status"])
        lease = row["lease"]
        if status in (
            EvaluationStatus.PENDING,
            EvaluationStatus.FAILED,
            EvaluationStatus.ENQUEUE_FAILED,
        ) or (status == EvaluationStatus.RUNNING and isinstance(lease, datetime) and lease < now):
            token = uuid4().hex
            row["status"] = EvaluationStatus.RUNNING
            row["token"] = token
            row["lease"] = now + timedelta(seconds=lease_seconds)
            return token
        return None

    async def extend_lease(
        self, *, evaluation_id: UUID, claim_token: str, lease_seconds: int
    ) -> bool:
        row = self._rows.get(evaluation_id)
        if not row or row.get("token") != claim_token or row["status"] != EvaluationStatus.RUNNING:
            return False
        row["lease"] = datetime.now(tz=UTC) + timedelta(seconds=lease_seconds)
        return True

    async def recover_stale_leases(self, *, batch_size: int) -> list[RecoveredEvaluation]:
        now = datetime.now(tz=UTC)
        out: list[RecoveredEvaluation] = []
        for ev_id, row in list(self._rows.items())[:batch_size]:
            lease = row["lease"]
            if (
                row["status"] == EvaluationStatus.RUNNING
                and isinstance(lease, datetime)
                and lease < now
            ):
                row["status"] = EvaluationStatus.PENDING
                row["token"] = None
                row["lease"] = None
                out.append(
                    RecoveredEvaluation(
                        evaluation_id=ev_id,
                        knowledge_base_id=row["kb"],  # type: ignore[arg-type]
                        organization_id=row["org"],  # type: ignore[arg-type]
                    ),
                )
        return out

    async def mark_running(self, *, evaluation_id: UUID) -> None:
        row = self._rows.get(evaluation_id)
        if row:
            row["status"] = EvaluationStatus.RUNNING

    async def mark_failed(
        self, *, evaluation_id: UUID, error_message: str, claim_token: str
    ) -> bool:
        row = self._rows.get(evaluation_id)
        if not row or row.get("token") != claim_token:
            return False
        row["status"] = EvaluationStatus.FAILED
        row["metrics"] = error_message
        row["token"] = None
        return True

    async def get_by_id_for_knowledge_base(
        self,
        evaluation_id: UUID,
        knowledge_base_id: UUID,
    ) -> EvaluationRecord | None:
        row = self._rows.get(evaluation_id)
        if row is None or row["kb"] != knowledge_base_id:
            return None
        return self._rec(evaluation_id)

    async def get_scoped(
        self,
        *,
        evaluation_id: UUID,
        knowledge_base_id: UUID,
        organization_id: UUID,
    ) -> EvaluationRecord | None:
        row = self._rows.get(evaluation_id)
        if row is None or row["kb"] != knowledge_base_id or row["org"] != organization_id:
            return None
        return self._rec(evaluation_id)

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
        row = self._rows.get(evaluation_id)
        if not row or row.get("token") != claim_token:
            return False
        _ = (question, expected, answer, score)
        return True

    async def mark_completed(
        self,
        *,
        evaluation_id: UUID,
        metrics: dict[str, Any],
        claim_token: str,
    ) -> bool:
        row = self._rows.get(evaluation_id)
        if not row or row.get("token") != claim_token:
            return False
        row["status"] = EvaluationStatus.COMPLETED
        row["metrics"] = str(metrics)
        row["token"] = None
        return True
