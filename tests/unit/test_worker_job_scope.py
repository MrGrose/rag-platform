from datetime import UTC, datetime
from uuid import uuid4

import pytest

from rag_platform.application.validation.worker_jobs import assert_evaluation_job_scope
from rag_platform.domain.entities import Document
from rag_platform.domain.enums import DocumentStatus
from rag_platform.domain.errors import NotFoundError, ValidationError
from rag_platform.infrastructure.fakes.evaluation_repository import InMemoryEvaluationRepository


class _DocRepo:
    def __init__(self, doc: Document) -> None:
        self._doc = doc

    async def get_by_id(self, _did):
        return self._doc


@pytest.mark.asyncio
async def test_evaluation_job_scope_mismatch_raises() -> None:
    org_a, org_b = uuid4(), uuid4()
    kb = uuid4()
    eval_id = uuid4()
    repo = InMemoryEvaluationRepository()
    await repo.seed(eval_id, kb, org_a, status="pending", metrics_json=None)
    with pytest.raises(NotFoundError):
        await assert_evaluation_job_scope(
            eval_repo=repo,
            evaluation_id=eval_id,
            knowledge_base_id=kb,
            organization_id=org_b,
        )


@pytest.mark.asyncio
async def test_document_job_scope_wrong_kb() -> None:
    now = datetime.now(tz=UTC)
    doc = Document(
        id=uuid4(),
        knowledge_base_id=uuid4(),
        organization_id=uuid4(),
        filename="a.txt",
        mime_type="text/plain",
        size_bytes=1,
        status=DocumentStatus.UPLOADED,
        storage_key="k",
        content_hash="h",
        content_version=1,
        error_message=None,
        deleted_at=None,
        created_at=now,
        updated_at=now,
    )
    from rag_platform.application.validation.worker_jobs import assert_document_job_scope

    with pytest.raises(ValidationError):
        await assert_document_job_scope(
            doc_repo=_DocRepo(doc),
            document_id=doc.id,
            knowledge_base_id=uuid4(),
            organization_id=doc.organization_id,
        )
