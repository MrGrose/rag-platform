from uuid import UUID

from rag_platform.application.ports.evaluations import EvaluationRepository
from rag_platform.domain.entities import EvaluationRecord
from rag_platform.domain.errors import NotFoundError


class GetEvaluation:
    def __init__(self, *, eval_repo: EvaluationRepository) -> None:
        self._eval_repo = eval_repo

    async def execute(
        self,
        *,
        evaluation_id: UUID,
        knowledge_base_id: UUID,
        organization_id: UUID,
    ) -> EvaluationRecord:
        row = await self._eval_repo.get_scoped(
            evaluation_id=evaluation_id,
            knowledge_base_id=knowledge_base_id,
            organization_id=organization_id,
        )
        if row is None:
            raise NotFoundError(f"evaluation not found: {evaluation_id}")
        return row
