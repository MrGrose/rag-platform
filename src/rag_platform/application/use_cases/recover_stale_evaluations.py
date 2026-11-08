from collections.abc import Awaitable, Callable
from uuid import UUID

from rag_platform.application.ports.evaluations import EvaluationRepository
from rag_platform.config import get_settings

EnqueueRunEvaluation = Callable[[UUID, UUID, UUID], Awaitable[None]]


class RecoverStaleEvaluations:
    def __init__(
        self,
        *,
        eval_repo: EvaluationRepository,
        enqueue: EnqueueRunEvaluation,
    ) -> None:
        self._eval_repo = eval_repo
        self._enqueue = enqueue

    async def execute(self) -> int:
        settings = get_settings()
        recovered = await self._eval_repo.recover_stale_leases(
            batch_size=settings.evaluation_recovery_batch_size,
        )
        for row in recovered:
            await self._enqueue(row.evaluation_id, row.knowledge_base_id, row.organization_id)
        return len(recovered)
