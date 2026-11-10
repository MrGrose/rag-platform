"""Ingest three documents and ask three questions, printing answers with citations."""

import asyncio
from datetime import UTC, datetime
from pathlib import Path
from uuid import UUID

from rag_platform.application.use_cases.create_document import CreateDocument
from rag_platform.application.use_cases.process_document import ProcessDocument
from rag_platform.composition.http import build_chat
from rag_platform.infrastructure.db.chunk_repository import SqlAlchemyChunkRepository
from rag_platform.infrastructure.db.document_repository import SqlAlchemyDocumentRepository
from rag_platform.infrastructure.db.repositories import (
    SqlAlchemyKnowledgeBaseRepository,
    SqlAlchemyOrganizationRepository,
)
from rag_platform.infrastructure.db.session import session_scope
from rag_platform.infrastructure.fakes.storage import InMemoryObjectStorage
from rag_platform.infrastructure.parsing.registry import default_parser_registry
from rag_platform.infrastructure.providers.factory import build_embeddings

ROOT = Path(__file__).resolve().parents[1]
CORPUS = ROOT / "examples" / "corpus"
DOCUMENTS = ["refund-policy.md", "delivery-terms.md", "warranty.md"]
QUESTIONS = [
    "How many days do customers have to return most items?",
    "What does express delivery cost and how fast is it?",
    "How long is the hardware warranty?",
]


class _NoopVersion:
    async def bump(self, knowledge_base_id: str) -> None:
        return None

    async def current(self, knowledge_base_id: str) -> str:
        return "0"


async def _prepare() -> UUID:
    async with session_scope() as session:
        org_repo = SqlAlchemyOrganizationRepository(session)
        org = await org_repo.get_by_name("demo")
        if org is None:
            org = await org_repo.create("demo")
        kb = await SqlAlchemyKnowledgeBaseRepository(session).create(
            org.id, f"demo-{datetime.now(tz=UTC):%H%M%S}"
        )
        return kb.id


async def _ingest(kb_id: UUID) -> None:
    storage = InMemoryObjectStorage()
    embeddings = build_embeddings()
    async with session_scope() as session:
        doc_repo = SqlAlchemyDocumentRepository(session)
        chunk_repo = SqlAlchemyChunkRepository(session)

        async def noop(*_args) -> None:
            return None

        creator = CreateDocument(
            kb_repo=SqlAlchemyKnowledgeBaseRepository(session),
            doc_repo=doc_repo,
            storage=storage,
            kb_version=_NoopVersion(),
            enqueue_process=noop,
        )
        processor = ProcessDocument(
            doc_repo=doc_repo,
            chunk_repo=chunk_repo,
            storage=storage,
            embeddings=embeddings,
            parsers=default_parser_registry(),
        )
        for name in DOCUMENTS:
            path = CORPUS / name
            document = await creator.execute(
                knowledge_base_id=kb_id,
                filename=path.name,
                mime_type="text/markdown",
                content=path.read_bytes(),
            )
            await processor.execute(document.id)


async def main() -> None:
    kb_id = await _prepare()
    await _ingest(kb_id)
    print(f"knowledge base: {kb_id}\n")
    async with session_scope() as session:
        chat = await build_chat(session, kb_id)
        for question in QUESTIONS:
            result = await chat.execute(knowledge_base_id=kb_id, question=question)
            print(f"Q: {question}")
            print(f"A: {result.answer}")
            print(f"   citations: {len(result.citations)}")
            for citation in result.citations[:3]:
                print(f"   - {citation.snippet[:120]}")
            print()


if __name__ == "__main__":
    asyncio.run(main())
