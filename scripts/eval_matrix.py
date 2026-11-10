"""Compare retrieval configurations on the example corpus.

Runs vector-only and hybrid retrieval with and without the bge reranker, for
fake and bge-m3 embeddings, and writes a markdown table with hit@5, MRR@5 and
latency. No LLM calls: this measures retrieval, not answer generation.

    python scripts/eval_matrix.py --limit 20
"""

import argparse
import asyncio
import json
import statistics
import time
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from uuid import UUID

from sqlalchemy import text

from rag_platform.application.use_cases.create_document import CreateDocument
from rag_platform.application.use_cases.process_document import ProcessDocument
from rag_platform.config import Settings
from rag_platform.infrastructure.db.chunk_repository import SqlAlchemyChunkRepository
from rag_platform.infrastructure.db.document_repository import SqlAlchemyDocumentRepository
from rag_platform.infrastructure.db.repositories import (
    SqlAlchemyKnowledgeBaseRepository,
    SqlAlchemyOrganizationRepository,
)
from rag_platform.infrastructure.db.retrieval_engine import PgHybridRetrievalEngine
from rag_platform.infrastructure.db.session import session_scope
from rag_platform.infrastructure.fakes.storage import InMemoryObjectStorage
from rag_platform.infrastructure.parsing.registry import default_parser_registry
from rag_platform.infrastructure.providers.factory import build_embeddings, build_reranker

ROOT = Path(__file__).resolve().parents[1]
CORPUS = ROOT / "examples" / "corpus"
DATASET = ROOT / "evals" / "matrix_dataset.json"
DISTRACTORS = ROOT / "examples" / "corpus_distractors"
REPORTS = ROOT / "reports"
TOP_K = 20


class _NoopVersion:
    async def bump(self, knowledge_base_id: str) -> None:
        return None

    async def current(self, knowledge_base_id: str) -> str:
        return "0"


def _settings(provider: str) -> Settings:
    return Settings(
        APP_ENV="test",
        EMBEDDINGS_PROVIDER=provider,
        EMBEDDINGS_DEVICE="cpu",
        EMBEDDINGS_BATCH_SIZE=16,
        RERANKER_PROVIDER="off",
        LLM_PROVIDER="fake",
    )


async def _prepare_kb(label: str) -> UUID:
    async with session_scope() as session:
        org_repo = SqlAlchemyOrganizationRepository(session)
        org = await org_repo.get_by_name("eval-matrix")
        if org is None:
            org = await org_repo.create("eval-matrix")
        suffix = datetime.now(tz=UTC).strftime("%H%M%S")
        kb = await SqlAlchemyKnowledgeBaseRepository(session).create(org.id, f"{label}-{suffix}")
        return kb.id


async def _ingest(kb_id: UUID, settings: Settings, extra: Path | None = None) -> dict[UUID, str]:
    storage = InMemoryObjectStorage()
    embeddings = build_embeddings(settings)
    async with session_scope() as session:
        doc_repo = SqlAlchemyDocumentRepository(session)
        chunk_repo = SqlAlchemyChunkRepository(session)

        async def noop(*_args: Any) -> None:
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
        paths = sorted(CORPUS.glob("*.md"))
        if extra is not None and extra.is_dir():
            paths += sorted(extra.glob("*.md"))
        for path in paths:
            document = await creator.execute(
                knowledge_base_id=kb_id,
                filename=path.name,
                mime_type="text/markdown",
                content=path.read_bytes(),
            )
            await processor.execute(document.id)

    async with session_scope() as session:
        rows = await session.execute(
            text(
                """
                SELECT dc.id, d.filename
                FROM document_chunks dc
                JOIN documents d ON d.id = dc.document_id
                WHERE dc.knowledge_base_id = :kb_id
                """
            ),
            {"kb_id": kb_id},
        )
        return {row[0]: row[1] for row in rows}


def _score(expected: list[str], sources: list[str], k: int) -> tuple[bool, float]:
    top = sources[:k]
    hit = bool(expected) and all(source in top for source in expected)
    reciprocal = 0.0
    for rank, source in enumerate(top, start=1):
        if source in expected:
            reciprocal = 1.0 / rank
            break
    return hit, reciprocal


async def _run_config(
    kb_id: UUID,
    sources_by_chunk: dict[UUID, str],
    settings: Settings,
    *,
    mode: str,
    reranker_name: str,
    items: list[dict],
) -> dict:
    embeddings = build_embeddings(settings)
    reranker = build_reranker(
        Settings(
            APP_ENV="test",
            ALLOW_FAKE_PROVIDERS=True,
            RERANKER_PROVIDER=reranker_name,
            EMBEDDINGS_PROVIDER=settings.embeddings_provider,
        )
    )
    hits: list[bool] = []
    top1: list[bool] = []
    reciprocal: list[float] = []
    latencies: list[float] = []
    org_id = await _org_id(kb_id)
    async with session_scope() as session:
        engine = PgHybridRetrievalEngine(session, embeddings, mode=mode)
        for item in items:
            started = time.perf_counter()
            retrieved = await engine.retrieve(
                organization_id=org_id,
                knowledge_base_id=kb_id,
                question=item["question"],
                limit=TOP_K,
            )
            ranked = await reranker.rerank(item["question"], retrieved, 5)
            latencies.append((time.perf_counter() - started) * 1000)
            names = [
                sources_by_chunk[hit.chunk_id] for hit in ranked if hit.chunk_id in sources_by_chunk
            ]
            hit, rr = _score(item["expected_sources"], names, 5)
            hits.append(hit)
            reciprocal.append(rr)
            top1.append(bool(names) and names[0] in item["expected_sources"])
    return {
        "mode": mode,
        "reranker": reranker_name,
        "hit_at_5": sum(hits) / max(1, len(hits)),
        "hit_at_1": sum(top1) / max(1, len(top1)),
        "mrr_at_5": sum(reciprocal) / max(1, len(reciprocal)),
        "p50_ms": statistics.median(latencies),
    }


async def _org_id(kb_id: UUID) -> UUID:
    async with session_scope() as session:
        row = await session.execute(
            text("SELECT organization_id FROM knowledge_bases WHERE id = :kb_id"),
            {"kb_id": kb_id},
        )
        return row.scalar_one()


async def run(limit: int | None, report_path: Path, dataset: Path | None = None) -> list[dict]:
    source = dataset or DATASET
    items = [item for item in json.loads(source.read_text(encoding="utf-8")) if item["answerable"]]
    if limit:
        items = items[:limit]
    rows: list[dict] = []
    for provider in ("fake", "bge_m3"):
        settings = _settings(provider)
        try:
            kb_id = await _prepare_kb(provider)
            sources_by_chunk = await _ingest(kb_id, settings, DISTRACTORS)
        except Exception as exc:
            print(f"skip {provider}: {exc}")
            continue
        for mode in ("vector", "hybrid"):
            for reranker_name in ("off", "bge_reranker"):
                result = await _run_config(
                    kb_id,
                    sources_by_chunk,
                    settings,
                    mode=mode,
                    reranker_name=reranker_name,
                    items=items,
                )
                result["embeddings"] = provider
                rows.append(result)
                print(json.dumps(result, ensure_ascii=False))
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(_render(rows, len(items)), encoding="utf-8")
    print(f"report: {report_path}")
    return rows


def _render(rows: list[dict], questions: int) -> str:
    lines = [
        f"# Retrieval matrix {datetime.now(tz=UTC):%Y-%m-%d}",
        "",
        f"Corpus: {len(list(CORPUS.glob('*.md')) + list(DISTRACTORS.glob('*.md')))} documents "
        f"(including distractors), {questions} answerable questions.",
        "Metrics are retrieval-only: no LLM call, reranker limited to five hits.",
        "",
        "| Embeddings | Retrieval | Reranker | hit@1 | hit@5 | MRR@5 | p50, ms |",
        "|------------|-----------|----------|-------|-------|-------|---------|",
    ]
    for row in rows:
        lines.append(
            f"| {row['embeddings']} | {row['mode']} | {row['reranker']} | "
            f"{row['hit_at_1']:.3f} | {row['hit_at_5']:.3f} | "
            f"{row['mrr_at_5']:.3f} | {row['p50_ms']:.1f} |"
        )
    lines.append("")
    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--limit", type=int, default=None)
    parser.add_argument("--dataset", type=Path, default=None)
    parser.add_argument("--report", type=Path, default=None)
    args = parser.parse_args()
    report = args.report or REPORTS / f"eval-matrix-{datetime.now(tz=UTC):%Y-%m-%d}.md"
    asyncio.run(run(args.limit, report, args.dataset))


if __name__ == "__main__":
    main()
