"""Run the retrieval evaluation over the example corpus.

Ingests ``examples/corpus`` into a fresh knowledge base, asks every question
from ``evals/dataset.json`` through the real chat pipeline, then writes a
markdown report with retrieval quality, answer quality, latency and token use.

Usage:
    python scripts/eval.py --limit 10
    EMBEDDINGS_PROVIDER=bge_m3 LLM_PROVIDER=openai python scripts/eval.py
"""

import argparse
import asyncio
import json
import time
from datetime import UTC, datetime
from pathlib import Path
from uuid import UUID

from sqlalchemy import text

from rag_platform.application.use_cases.create_document import CreateDocument
from rag_platform.application.use_cases.process_document import ProcessDocument
from rag_platform.composition.http import build_chat
from rag_platform.config import get_settings
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
DATASET = ROOT / "evals" / "dataset.json"
REPORTS = ROOT / "reports"


class _NoopVersion:
    async def bump(self, knowledge_base_id: str) -> None:
        return None

    async def current(self, knowledge_base_id: str) -> str:
        return "0"


def _percentile(values: list[float], share: float) -> float:
    if not values:
        return 0.0
    ordered = sorted(values)
    index = min(len(ordered) - 1, max(0, round(share * (len(ordered) - 1))))
    return ordered[index]


async def _prepare_kb() -> tuple[UUID, UUID]:
    async with session_scope() as session:
        org_repo = SqlAlchemyOrganizationRepository(session)
        org = await org_repo.get_by_name("eval-corpus")
        if org is None:
            org = await org_repo.create("eval-corpus")
        kb_repo = SqlAlchemyKnowledgeBaseRepository(session)
        kb = await kb_repo.create(org.id, f"eval-{datetime.now(tz=UTC):%Y%m%d-%H%M%S}")
        return org.id, kb.id


async def _ingest(kb_id: UUID, files: list[Path]) -> int:
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
        for path in files:
            document = await creator.execute(
                knowledge_base_id=kb_id,
                filename=path.name,
                mime_type="text/markdown",
                content=path.read_bytes(),
            )
            await processor.execute(document.id)
        return len(files)


async def _top_sources(kb_id: UUID, query_id: UUID) -> list[str]:
    async with session_scope() as session:
        rows = await session.execute(
            text(
                """
                SELECT d.filename
                FROM retrieval_results rr
                JOIN documents d ON d.id = rr.document_id
                WHERE rr.query_id = :query_id AND rr.knowledge_base_id = :kb_id
                ORDER BY rr.rank
                LIMIT 5
                """
            ),
            {"query_id": query_id, "kb_id": kb_id},
        )
        return [row[0] for row in rows]


async def _usage(query_id: UUID) -> tuple[int, int, float]:
    async with session_scope() as session:
        row = (
            await session.execute(
                text(
                    """
                    SELECT coalesce(sum(prompt_tokens), 0),
                           coalesce(sum(completion_tokens), 0),
                           coalesce(sum(estimated_cost_usd), 0)
                    FROM llm_requests WHERE query_id = :query_id
                    """
                ),
                {"query_id": query_id},
            )
        ).one()
        return int(row[0]), int(row[1]), float(row[2])


def _fact_match(answer: str, facts: list[str]) -> bool:
    lowered = answer.lower()
    return bool(facts) and all(fact.lower() in lowered for fact in facts)


async def run(limit: int | None, report_path: Path, ids: str | None = None) -> dict:
    settings = get_settings()
    items = json.loads(DATASET.read_text(encoding="utf-8"))
    if ids:
        wanted = {value.strip() for value in ids.split(",") if value.strip()}
        items = [item for item in items if item["id"] in wanted]
    if limit:
        items = items[:limit]
    files = sorted(CORPUS.glob("*.md"))
    _org_id, kb_id = await _prepare_kb()
    ingested = await _ingest(kb_id, files)
    print(f"ingested {ingested} documents into kb {kb_id}")

    async with session_scope() as session:
        chat = await build_chat(session, kb_id)

    rows: list[dict] = []
    async with session_scope() as session:
        chat = await build_chat(session, kb_id)
        for item in items:
            started = time.perf_counter()
            result = await chat.execute(knowledge_base_id=kb_id, question=item["question"])
            latency = time.perf_counter() - started
            await session.commit()
            sources = await _top_sources(kb_id, result.query_id)
            prompt_tokens, completion_tokens, cost = await _usage(result.query_id)
            answer = result.answer or ""
            answerable = bool(item["answerable"])
            rows.append(
                {
                    "id": item["id"],
                    "question": item["question"],
                    "answerable": answerable,
                    "answer": answer,
                    "expected_sources": item["expected_sources"],
                    "sources": sources,
                    "hit": bool(item["expected_sources"])
                    and all(source in sources for source in item["expected_sources"]),
                    "refusal": bool(result.insufficient_context),
                    "refusal_correct": (not result.insufficient_context)
                    if answerable
                    else result.insufficient_context,
                    "citations": len(result.citations),
                    "fact_match": _fact_match(answer, item["expected_facts"])
                    if answerable
                    else None,
                    "latency_s": latency,
                    "prompt_tokens": prompt_tokens,
                    "completion_tokens": completion_tokens,
                    "cost_usd": cost,
                }
            )

    answerable_rows = [row for row in rows if row["answerable"]]
    unanswerable_rows = [row for row in rows if not row["answerable"]]
    latencies = [row["latency_s"] for row in rows]
    metrics = {
        "documents": ingested,
        "questions": len(rows),
        "answerable": len(answerable_rows),
        "unanswerable": len(unanswerable_rows),
        "hit_at_5": sum(row["hit"] for row in answerable_rows) / max(1, len(answerable_rows)),
        "citation_rate": sum(row["citations"] > 0 for row in answerable_rows)
        / max(1, len(answerable_rows)),
        "fact_match": sum(bool(row["fact_match"]) for row in answerable_rows)
        / max(1, len(answerable_rows)),
        "refusal_correct": sum(row["refusal_correct"] for row in rows) / max(1, len(rows)),
        "latency_p50_s": _percentile(latencies, 0.5),
        "latency_p95_s": _percentile(latencies, 0.95),
        "prompt_tokens": sum(row["prompt_tokens"] for row in rows),
        "completion_tokens": sum(row["completion_tokens"] for row in rows),
        "cost_usd": sum(row["cost_usd"] for row in rows),
        "embeddings_provider": settings.embeddings_provider,
        "reranker_provider": settings.reranker_provider,
        "llm_provider": settings.llm_provider,
        "llm_model": settings.llm_model if settings.llm_provider != "fake" else "fake-llm-v1",
    }
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(_render(metrics, rows), encoding="utf-8")
    print(json.dumps(metrics, indent=2))
    print(f"report: {report_path}")
    return {"metrics": metrics, "rows": rows}


def _render(metrics: dict, rows: list[dict]) -> str:
    failures = [
        row
        for row in rows
        if not row["refusal_correct"]
        or (row["answerable"] and not row["hit"])
        or (row["answerable"] and row["fact_match"] is False)
    ]
    lines = [
        f"# Evaluation {datetime.now(tz=UTC):%Y-%m-%d}",
        "",
        f"Providers: embeddings `{metrics['embeddings_provider']}`, "
        f"reranker `{metrics['reranker_provider']}`, LLM `{metrics['llm_provider']}` "
        f"(`{metrics['llm_model']}`).",
        "",
        f"Corpus: {metrics['documents']} documents, {metrics['questions']} questions "
        f"({metrics['answerable']} answerable, {metrics['unanswerable']} without an answer).",
        "",
        "| Metric | Value |",
        "|--------|-------|",
        f"| hit@5 | {metrics['hit_at_5']:.3f} |",
        f"| citation rate | {metrics['citation_rate']:.3f} |",
        f"| answer fact match | {metrics['fact_match']:.3f} |",
        f"| refusal correctness | {metrics['refusal_correct']:.3f} |",
        f"| latency p50 | {metrics['latency_p50_s']:.2f} s |",
        f"| latency p95 | {metrics['latency_p95_s']:.2f} s |",
        f"| tokens | {metrics['prompt_tokens']} in / {metrics['completion_tokens']} out |",
        f"| estimated cost | ${metrics['cost_usd']:.4f} |",
        "",
        "## Failures",
        "",
    ]
    if not failures:
        lines.append("None.")
    else:
        for row in failures:
            lines.append(
                f"- `{row['id']}` {row['question']} sources={row['sources']} "
                f"refusal={row['refusal']} answer={row['answer'][:120]!r}"
            )
    lines.append("")
    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--limit", type=int, default=None)
    parser.add_argument("--ids", default=None, help="comma separated question ids")
    parser.add_argument("--report", type=Path, default=None)
    args = parser.parse_args()
    report = args.report or REPORTS / f"eval-{datetime.now(tz=UTC):%Y-%m-%d}.md"
    asyncio.run(run(args.limit, report, args.ids))


if __name__ == "__main__":
    main()
