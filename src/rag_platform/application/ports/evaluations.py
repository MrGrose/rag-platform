from dataclasses import dataclass
from typing import Any, Protocol
from uuid import UUID

from rag_platform.domain.entities import EvaluationRecord


@dataclass(frozen=True)
class RecoveredEvaluation:
    evaluation_id: UUID
    knowledge_base_id: UUID
    organization_id: UUID


class EvaluationRepository(Protocol):
    async def create_pending(
        self,
        *,
        evaluation_id: UUID,
        knowledge_base_id: UUID,
        organization_id: UUID,
    ) -> None: ...

    async def mark_enqueue_failed(self, *, evaluation_id: UUID) -> None: ...

    async def mark_running(self, *, evaluation_id: UUID) -> None: ...

    async def try_claim_running(
        self,
        *,
        evaluation_id: UUID,
        lease_seconds: int,
    ) -> str | None: ...

    async def extend_lease(
        self,
        *,
        evaluation_id: UUID,
        claim_token: str,
        lease_seconds: int,
    ) -> bool: ...

    async def recover_stale_leases(self, *, batch_size: int) -> list[RecoveredEvaluation]: ...

    async def mark_failed(
        self,
        *,
        evaluation_id: UUID,
        error_message: str,
        claim_token: str,
    ) -> bool: ...

    async def add_result(
        self,
        *,
        evaluation_id: UUID,
        question: str,
        expected: str,
        answer: str,
        score: float,
        claim_token: str,
    ) -> bool: ...

    async def mark_completed(
        self,
        *,
        evaluation_id: UUID,
        metrics: dict[str, Any],
        claim_token: str,
    ) -> bool: ...

    async def get_by_id_for_knowledge_base(
        self,
        evaluation_id: UUID,
        knowledge_base_id: UUID,
    ) -> EvaluationRecord | None: ...

    async def get_scoped(
        self,
        *,
        evaluation_id: UUID,
        knowledge_base_id: UUID,
        organization_id: UUID,
    ) -> EvaluationRecord | None: ...
