from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from rag_platform.application.use_cases.process_document import ProcessDocument
from rag_platform.application.use_cases.run_evaluation import RunEvaluation
from rag_platform.composition.http import build_run_evaluation
from rag_platform.infrastructure.cache.kb_version_adapter import RedisKnowledgeBaseVersionPort
from rag_platform.infrastructure.db.chunk_repository import SqlAlchemyChunkRepository
from rag_platform.infrastructure.db.document_repository import SqlAlchemyDocumentRepository
from rag_platform.infrastructure.parsing.registry import default_parser_registry
from rag_platform.infrastructure.providers.cached_embeddings import CachedEmbeddingProvider
from rag_platform.infrastructure.providers.factory import build_embeddings
from rag_platform.infrastructure.storage.s3 import S3ObjectStorage


async def build_process_document(session: AsyncSession, document_id: UUID) -> ProcessDocument:
    doc_repo = SqlAlchemyDocumentRepository(session)
    document = await doc_repo.get_by_id(document_id)
    kb_id = str(document.knowledge_base_id) if document else "unknown"
    version = await RedisKnowledgeBaseVersionPort().current(kb_id)
    embeddings = CachedEmbeddingProvider(build_embeddings(), version)
    return ProcessDocument(
        doc_repo=doc_repo,
        chunk_repo=SqlAlchemyChunkRepository(session),
        storage=S3ObjectStorage(),
        embeddings=embeddings,
        parsers=default_parser_registry(),
    )


async def build_worker_run_evaluation(
    session: AsyncSession,
    knowledge_base_id: UUID,
) -> RunEvaluation:
    return await build_run_evaluation(session, knowledge_base_id)
