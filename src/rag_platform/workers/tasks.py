from uuid import UUID

from rag_platform.application.use_cases.recover_stale_evaluations import RecoverStaleEvaluations
from rag_platform.application.use_cases.requeue_stale_documents import RequeueStaleDocuments
from rag_platform.application.validation.worker_jobs import (
    assert_document_job_scope,
    assert_evaluation_job_scope,
)
from rag_platform.composition.worker import build_process_document, build_worker_run_evaluation
from rag_platform.infrastructure.db.chunk_repository import SqlAlchemyChunkRepository
from rag_platform.infrastructure.db.document_repository import SqlAlchemyDocumentRepository
from rag_platform.infrastructure.db.evaluation_repository import SqlAlchemyEvaluationRepository
from rag_platform.infrastructure.db.session import session_scope
from rag_platform.infrastructure.queue.arq import enqueue_process_document, enqueue_run_evaluation


async def process_document(
    ctx: dict,
    document_id: str,
    knowledge_base_id: str,
    organization_id: str,
) -> str:
    _ = ctx
    doc_uuid = UUID(document_id)
    kb_uuid = UUID(knowledge_base_id)
    org_uuid = UUID(organization_id)
    async with session_scope() as session:
        doc_repo = SqlAlchemyDocumentRepository(session)
        await assert_document_job_scope(
            doc_repo=doc_repo,
            document_id=doc_uuid,
            knowledge_base_id=kb_uuid,
            organization_id=org_uuid,
        )
        use_case = await build_process_document(session, doc_uuid)
        result = await use_case.execute(doc_uuid)
        return str(result.status)


async def delete_document_vectors(
    ctx: dict,
    document_id: str,
    knowledge_base_id: str,
    organization_id: str,
) -> str:
    _ = ctx
    doc_uuid = UUID(document_id)
    kb_uuid = UUID(knowledge_base_id)
    org_uuid = UUID(organization_id)
    async with session_scope() as session:
        await assert_document_job_scope(
            doc_repo=SqlAlchemyDocumentRepository(session),
            document_id=doc_uuid,
            knowledge_base_id=kb_uuid,
            organization_id=org_uuid,
        )
        repo = SqlAlchemyChunkRepository(session)
        await repo.delete_for_document(doc_uuid)
    return "deleted"


async def reindex_document(
    ctx: dict,
    document_id: str,
    knowledge_base_id: str,
    organization_id: str,
) -> str:
    return await process_document(ctx, document_id, knowledge_base_id, organization_id)


async def run_evaluation(
    ctx: dict,
    evaluation_id: str,
    knowledge_base_id: str,
    organization_id: str,
) -> str:
    _ = ctx
    eval_uuid = UUID(evaluation_id)
    kb_uuid = UUID(knowledge_base_id)
    org_uuid = UUID(organization_id)
    async with session_scope() as session:
        eval_repo = SqlAlchemyEvaluationRepository(session)
        await assert_evaluation_job_scope(
            eval_repo=eval_repo,
            evaluation_id=eval_uuid,
            knowledge_base_id=kb_uuid,
            organization_id=org_uuid,
        )
        use_case = await build_worker_run_evaluation(session, kb_uuid)
        result_id = await use_case.execute(
            evaluation_id=eval_uuid,
            knowledge_base_id=kb_uuid,
            organization_id=org_uuid,
        )
        return str(result_id)


async def recover_stale_evaluations(ctx: dict) -> str:
    _ = ctx

    async def _enqueue(evaluation_id: UUID, knowledge_base_id: UUID, organization_id: UUID) -> None:
        await enqueue_run_evaluation(evaluation_id, knowledge_base_id, organization_id)

    async with session_scope() as session:
        use_case = RecoverStaleEvaluations(
            eval_repo=SqlAlchemyEvaluationRepository(session),
            enqueue=_enqueue,
        )
        count = await use_case.execute()
        await session.commit()
    return str(count)


async def recover_stale_documents(ctx: dict) -> str:
    _ = ctx

    async def _enqueue(document_id: UUID, knowledge_base_id: UUID, organization_id: UUID) -> None:
        await enqueue_process_document(document_id, knowledge_base_id, organization_id)

    async with session_scope() as session:
        use_case = RequeueStaleDocuments(
            doc_repo=SqlAlchemyDocumentRepository(session),
            enqueue=_enqueue,
        )
        count = await use_case.execute()
    return str(count)


_worker_shutdown = False


async def worker_shutdown(ctx: dict) -> None:
    global _worker_shutdown
    _worker_shutdown = True
    _ = ctx


async def noop(ctx: dict) -> str:
    _ = ctx
    return "ok"
