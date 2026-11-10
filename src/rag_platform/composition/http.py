import json
from pathlib import Path
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from rag_platform.application.ports.storage import ObjectStorage
from rag_platform.application.use_cases.chat import Chat
from rag_platform.application.use_cases.create_document import CreateDocument
from rag_platform.application.use_cases.delete_document import DeleteDocument
from rag_platform.application.use_cases.get_document import GetDocument
from rag_platform.application.use_cases.get_evaluation import GetEvaluation
from rag_platform.application.use_cases.get_query import GetQuery
from rag_platform.application.use_cases.list_documents import ListDocuments
from rag_platform.application.use_cases.run_evaluation import RunEvaluation
from rag_platform.application.use_cases.start_evaluation import StartEvaluation
from rag_platform.config import get_settings
from rag_platform.infrastructure.cache.kb_version_adapter import RedisKnowledgeBaseVersionPort
from rag_platform.infrastructure.chat.redis_resource_guard import RedisChatResourceGuard
from rag_platform.infrastructure.db.document_repository import SqlAlchemyDocumentRepository
from rag_platform.infrastructure.db.evaluation_repository import SqlAlchemyEvaluationRepository
from rag_platform.infrastructure.db.llm_request_log import SqlAlchemyLlmRequestLog
from rag_platform.infrastructure.db.outbox_repository import SqlAlchemyOutboxRepository
from rag_platform.infrastructure.db.query_repository import SqlAlchemyQueryRepository
from rag_platform.infrastructure.db.repositories import SqlAlchemyKnowledgeBaseRepository
from rag_platform.infrastructure.db.retrieval_engine import PgHybridRetrievalEngine
from rag_platform.infrastructure.fakes.chat_resource_guard import NoopChatResourceGuard
from rag_platform.infrastructure.providers.cached_embeddings import CachedEmbeddingProvider
from rag_platform.infrastructure.providers.factory import (
    build_embeddings,
    build_llm,
    build_reranker,
)
from rag_platform.infrastructure.queue.arq import (
    enqueue_delete_document_vectors,
    enqueue_process_document,
)
from rag_platform.infrastructure.retrieval.cached_retrieval import CachedRetrievalEngine
from rag_platform.infrastructure.telemetry.prometheus_chat import PrometheusChatObservability

_EVAL_DATASET = Path(__file__).resolve().parents[3] / "tests" / "fixtures" / "eval_dataset.json"


def _kb_version() -> RedisKnowledgeBaseVersionPort:
    return RedisKnowledgeBaseVersionPort()


async def build_chat(session: AsyncSession, knowledge_base_id: UUID) -> Chat:
    settings = get_settings()
    kb_version = await _kb_version().current(str(knowledge_base_id))
    embeddings = CachedEmbeddingProvider(build_embeddings(settings), kb_version)
    base_retrieval = PgHybridRetrievalEngine(session, embeddings)
    retrieval = CachedRetrievalEngine(base_retrieval)
    return Chat(
        kb_repo=SqlAlchemyKnowledgeBaseRepository(session),
        query_repo=SqlAlchemyQueryRepository(session),
        retrieval=retrieval,
        reranker=build_reranker(settings),
        llm=build_llm(settings),
        observability=PrometheusChatObservability(),
        llm_log=SqlAlchemyLlmRequestLog(session),
        resource_guard=(
            NoopChatResourceGuard()
            if get_settings().app_env.strip().lower() == "test"
            else RedisChatResourceGuard()
        ),
    )


def build_list_documents(session: AsyncSession) -> ListDocuments:
    return ListDocuments(doc_repo=SqlAlchemyDocumentRepository(session))


def build_get_document(session: AsyncSession) -> GetDocument:
    return GetDocument(doc_repo=SqlAlchemyDocumentRepository(session))


def build_get_query(session: AsyncSession) -> GetQuery:
    return GetQuery(query_repo=SqlAlchemyQueryRepository(session))


def build_get_evaluation(session: AsyncSession) -> GetEvaluation:
    return GetEvaluation(eval_repo=SqlAlchemyEvaluationRepository(session))


def build_start_evaluation(session: AsyncSession) -> StartEvaluation:
    return StartEvaluation(
        kb_repo=SqlAlchemyKnowledgeBaseRepository(session),
        eval_repo=SqlAlchemyEvaluationRepository(session),
        outbox_repo=SqlAlchemyOutboxRepository(session),
    )


def build_create_document(
    session: AsyncSession,
    storage: ObjectStorage,
) -> CreateDocument:
    async def _enqueue(document_id: UUID, knowledge_base_id: UUID, organization_id: UUID) -> None:
        await enqueue_process_document(document_id, knowledge_base_id, organization_id)

    return CreateDocument(
        kb_repo=SqlAlchemyKnowledgeBaseRepository(session),
        doc_repo=SqlAlchemyDocumentRepository(session),
        storage=storage,
        kb_version=_kb_version(),
        enqueue_process=_enqueue,
    )


def build_delete_document(session: AsyncSession) -> DeleteDocument:
    async def _enqueue(document_id: UUID, knowledge_base_id: UUID, organization_id: UUID) -> None:
        await enqueue_delete_document_vectors(document_id, knowledge_base_id, organization_id)

    return DeleteDocument(
        doc_repo=SqlAlchemyDocumentRepository(session),
        kb_version=_kb_version(),
        enqueue_cleanup=_enqueue,
    )


async def build_run_evaluation(session: AsyncSession, knowledge_base_id: UUID) -> RunEvaluation:
    dataset_items = json.loads(_EVAL_DATASET.read_text(encoding="utf-8"))
    chat = await build_chat(session, knowledge_base_id)
    return RunEvaluation(
        kb_repo=SqlAlchemyKnowledgeBaseRepository(session),
        eval_repo=SqlAlchemyEvaluationRepository(session),
        chat=chat,
        dataset_items=dataset_items,
    )
