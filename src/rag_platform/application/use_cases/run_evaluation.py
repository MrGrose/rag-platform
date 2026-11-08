from datetime import UTC, datetime
from uuid import UUID

from rag_platform.application.ports.evaluations import EvaluationRepository
from rag_platform.application.ports.repositories import KnowledgeBaseRepository
from rag_platform.application.use_cases.chat import Chat
from rag_platform.config import get_settings
from rag_platform.domain.enums import EvaluationStatus
from rag_platform.domain.errors import ConflictError, NotFoundError, ValidationError


class RunEvaluation:
    def __init__(
        self,
        *,
        kb_repo: KnowledgeBaseRepository,
        eval_repo: EvaluationRepository,
        chat: Chat,
        dataset_items: list[dict[str, str]],
    ) -> None:
        self._kb_repo = kb_repo
        self._eval_repo = eval_repo
        self._chat = chat
        self._dataset_items = dataset_items

    async def execute(
        self,
        *,
        evaluation_id: UUID,
        knowledge_base_id: UUID,
        organization_id: UUID,
    ) -> UUID:
        settings = get_settings()
        record = await self._eval_repo.get_scoped(
            evaluation_id=evaluation_id,
            knowledge_base_id=knowledge_base_id,
            organization_id=organization_id,
        )
        if record is None:
            raise NotFoundError(f"evaluation not found: {evaluation_id}")

        if record.status == EvaluationStatus.COMPLETED:
            return evaluation_id

        now = datetime.now(tz=UTC)
        if (
            record.status == EvaluationStatus.RUNNING
            and record.lease_expires_at is not None
            and record.lease_expires_at > now
        ):
            return evaluation_id

        if record.status not in (
            EvaluationStatus.PENDING,
            EvaluationStatus.ENQUEUE_FAILED,
            EvaluationStatus.FAILED,
            EvaluationStatus.RUNNING,
        ):
            raise ConflictError(f"evaluation not runnable: {record.status}")

        kb = await self._kb_repo.get_by_id(knowledge_base_id)
        if kb is None:
            raise NotFoundError(f"knowledge base not found: {knowledge_base_id}")
        if kb.organization_id != organization_id:
            raise ValidationError("organization scope mismatch")

        claim_token = await self._eval_repo.try_claim_running(
            evaluation_id=evaluation_id,
            lease_seconds=settings.evaluation_lease_seconds,
        )
        if claim_token is None:
            again = await self._eval_repo.get_scoped(
                evaluation_id=evaluation_id,
                knowledge_base_id=knowledge_base_id,
                organization_id=organization_id,
            )
            if again is None:
                raise NotFoundError(f"evaluation not found: {evaluation_id}")
            if again.status == EvaluationStatus.COMPLETED:
                return evaluation_id
            if (
                again.status == EvaluationStatus.RUNNING
                and again.lease_expires_at
                and again.lease_expires_at > now
            ):
                return evaluation_id
            raise ConflictError(f"evaluation not runnable: {again.status}")

        scores: list[float] = []
        try:
            for item in self._dataset_items:
                await self._eval_repo.extend_lease(
                    evaluation_id=evaluation_id,
                    claim_token=claim_token,
                    lease_seconds=settings.evaluation_lease_seconds,
                )
                result = await self._chat.execute(
                    knowledge_base_id=knowledge_base_id,
                    question=item["question"],
                )
                answer = (result.answer or "").lower()
                ok = item["expected_contains"].lower() in answer or bool(result.citations)
                score = 1.0 if ok else 0.0
                scores.append(score)
                if not await self._eval_repo.add_result(
                    evaluation_id=evaluation_id,
                    question=item["question"],
                    expected=item["expected_contains"],
                    answer=result.answer or "",
                    score=score,
                    claim_token=claim_token,
                ):
                    return evaluation_id
            await self._eval_repo.mark_completed(
                evaluation_id=evaluation_id,
                metrics={
                    "accuracy": sum(scores) / len(scores) if scores else 0.0,
                    "count": len(scores),
                },
                claim_token=claim_token,
            )
        except (TimeoutError, ConnectionError, OSError) as exc:
            await self._eval_repo.mark_failed(
                evaluation_id=evaluation_id,
                error_message=str(exc),
                claim_token=claim_token,
            )
            raise

        return evaluation_id
