from uuid import UUID

from rag_platform.application.ports.documents import DocumentRepository
from rag_platform.application.ports.evaluations import EvaluationRepository
from rag_platform.domain.errors import NotFoundError, ValidationError


async def assert_document_job_scope(
    *,
    doc_repo: DocumentRepository,
    document_id: UUID,
    knowledge_base_id: UUID,
    organization_id: UUID,
) -> None:
    document = await doc_repo.get_by_id(document_id)
    if document is None:
        raise NotFoundError(f"document not found: {document_id}")
    if document.knowledge_base_id != knowledge_base_id:
        raise ValidationError("document knowledge_base_id does not match job payload")
    if document.organization_id != organization_id:
        raise ValidationError("document organization_id does not match job payload")


async def assert_evaluation_job_scope(
    *,
    eval_repo: EvaluationRepository,
    evaluation_id: UUID,
    knowledge_base_id: UUID,
    organization_id: UUID,
) -> None:
    row = await eval_repo.get_scoped(
        evaluation_id=evaluation_id,
        knowledge_base_id=knowledge_base_id,
        organization_id=organization_id,
    )
    if row is None:
        raise NotFoundError(f"evaluation not found: {evaluation_id}")
