from uuid import UUID, uuid4

from rag_platform.application.ports.evaluations import EvaluationRepository
from rag_platform.application.ports.outbox import OutboxRepository
from rag_platform.application.ports.repositories import KnowledgeBaseRepository
from rag_platform.domain.entities import EvaluationRecord
from rag_platform.domain.enums import EvaluationStatus
from rag_platform.domain.errors import NotFoundError, ValidationError


class StartEvaluation:
    def __init__(
        self,
        *,
        kb_repo: KnowledgeBaseRepository,
        eval_repo: EvaluationRepository,
        outbox_repo: OutboxRepository,
    ) -> None:
        self._kb_repo = kb_repo
        self._eval_repo = eval_repo
        self._outbox_repo = outbox_repo

    async def execute(
        self,
        *,
        knowledge_base_id: UUID,
        organization_id: UUID,
    ) -> EvaluationRecord:
        kb = await self._kb_repo.get_by_id(knowledge_base_id)
        if kb is None:
            raise NotFoundError(f"knowledge base not found: {knowledge_base_id}")
        if kb.organization_id != organization_id:
            raise ValidationError("organization scope mismatch")

        evaluation_id = uuid4()
        await self._eval_repo.create_pending(
            evaluation_id=evaluation_id,
            knowledge_base_id=knowledge_base_id,
            organization_id=organization_id,
        )
        await self._outbox_repo.append(
            event_type="evaluation.run",
            aggregate_id=evaluation_id,
            organization_id=organization_id,
            payload={
                "evaluation_id": str(evaluation_id),
                "knowledge_base_id": str(knowledge_base_id),
                "organization_id": str(organization_id),
            },
        )

        return EvaluationRecord(
            id=evaluation_id,
            status=EvaluationStatus.PENDING,
            metrics_json=None,
        )
