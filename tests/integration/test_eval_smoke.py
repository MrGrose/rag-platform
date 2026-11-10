from pathlib import Path
from uuid import UUID, uuid4

import pytest
from sqlalchemy import text

from rag_platform.application.use_cases.create_document import CreateDocument
from rag_platform.application.use_cases.process_document import ProcessDocument
from rag_platform.composition.http import build_chat
from rag_platform.infrastructure.db.chunk_repository import SqlAlchemyChunkRepository
from rag_platform.infrastructure.db.document_repository import SqlAlchemyDocumentRepository
from rag_platform.infrastructure.db.repositories import (
    SqlAlchemyKnowledgeBaseRepository,
    SqlAlchemyOrganizationRepository,
)
from rag_platform.infrastructure.db.retrieval_engine import PgHybridRetrievalEngine
from rag_platform.infrastructure.db.session import session_scope
from rag_platform.infrastructure.fakes.kb_version import NoopKnowledgeBaseVersion
from rag_platform.infrastructure.fakes.storage import InMemoryObjectStorage
from rag_platform.infrastructure.parsing.registry import default_parser_registry
from rag_platform.infrastructure.providers.fake_embeddings import FakeEmbeddingProvider

ROOT = Path(__file__).resolve().parents[2]
CORPUS = ROOT / "examples" / "corpus"
DOCS = [
    "refund-policy.md",
    "delivery-terms.md",
    "warranty.md",
    "pricing.md",
    "support.md",
    "security.md",
    "onboarding.md",
    "sla.md",
]
QUESTIONS = [
    ("How many days do customers have to return most items?", "refund-policy.md"),
    ("What is the delivery fee for orders below 75 EUR?", "delivery-terms.md"),
    ("How long is the hardware warranty?", "warranty.md"),
    ("What is the price of the Basic plan?", "pricing.md"),
    ("When does support start in the morning?", "support.md"),
    ("Which encryption is used for data at rest?", "security.md"),
    ("How long is the trial?", "onboarding.md"),
    ("What is the monthly uptime target?", "sla.md"),
]


async def _seed() -> tuple[UUID, UUID]:
    storage = InMemoryObjectStorage()
    embeddings = FakeEmbeddingProvider()

    async def noop(_doc_id, _kb, _org) -> None:
        return None

    async with session_scope() as session:
        org = await SqlAlchemyOrganizationRepository(session).create(f"eval-{uuid4().hex[:8]}")
        kb = await SqlAlchemyKnowledgeBaseRepository(session).create(org.id, "eval-kb")
        doc_repo = SqlAlchemyDocumentRepository(session)
        chunk_repo = SqlAlchemyChunkRepository(session)

        creator = CreateDocument(
            kb_repo=SqlAlchemyKnowledgeBaseRepository(session),
            doc_repo=doc_repo,
            storage=storage,
            kb_version=NoopKnowledgeBaseVersion(),
            enqueue_process=noop,
        )
        processor = ProcessDocument(
            doc_repo=doc_repo,
            chunk_repo=chunk_repo,
            storage=storage,
            embeddings=embeddings,
            parsers=default_parser_registry(),
        )
        for name in DOCS:
            path = CORPUS / name
            document = await creator.execute(
                knowledge_base_id=kb.id,
                filename=path.name,
                mime_type="text/markdown",
                content=path.read_bytes(),
            )
            await processor.execute(document.id)
        return org.id, kb.id


@pytest.mark.integration
@pytest.mark.asyncio
async def test_eval_smoke_hit_rate_and_refusal() -> None:
    org_id, kb_id = await _seed()
    hits = 0
    async with session_scope() as session:
        engine = PgHybridRetrievalEngine(session, FakeEmbeddingProvider(), mode="hybrid")
        sources = {}
        rows = await session.execute(
            text(
                "SELECT dc.id, d.filename FROM document_chunks dc "
                "JOIN documents d ON d.id = dc.document_id "
                "WHERE dc.knowledge_base_id = :kb"
            ),
            {"kb": kb_id},
        )
        for chunk_id, filename in rows:
            sources[chunk_id] = filename

        for question, expected in QUESTIONS:
            found = await engine.retrieve(
                organization_id=org_id,
                knowledge_base_id=kb_id,
                question=question,
                limit=20,
            )
            names = [sources[hit.chunk_id] for hit in found[:5] if hit.chunk_id in sources]
            hits += int(expected in names)

    hit_at_5 = hits / len(QUESTIONS)
    assert hit_at_5 >= 0.75, f"hit@5={hit_at_5:.2f}"

    async with session_scope() as session:
        empty = await SqlAlchemyKnowledgeBaseRepository(session).create(
            org_id, f"empty-{uuid4().hex[:8]}"
        )
        chat = await build_chat(session, empty.id)
        result = await chat.execute(
            knowledge_base_id=empty.id,
            question="What is the CEO salary?",
        )
    assert result.insufficient_context is True
    assert result.citations == []
