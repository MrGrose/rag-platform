import asyncio
import time
from datetime import UTC, datetime
from uuid import UUID, uuid4

import structlog

from rag_platform.application.context.builder import build_context, estimate_tokens
from rag_platform.application.ports.chat_resources import ChatResourceGuard
from rag_platform.application.ports.llm import LlmProvider
from rag_platform.application.ports.llm_requests import LlmRequestLogPort
from rag_platform.application.ports.observability import ChatObservability
from rag_platform.application.ports.queries import QueryRepository
from rag_platform.application.ports.repositories import KnowledgeBaseRepository
from rag_platform.application.ports.reranker import RerankerProvider
from rag_platform.application.ports.retrieval import RetrievalEngine
from rag_platform.application.prompts.chat_v1 import (
    INSUFFICIENT_CONTEXT,
    PROMPT_VERSION,
    SYSTEM_PROMPT,
)
from rag_platform.application.prompts.safety import sanitize_user_question
from rag_platform.application.validation.citations import validate_citations
from rag_platform.config import get_settings
from rag_platform.domain.entities import ChatResult, Citation, Query
from rag_platform.domain.enums import QueryStatus
from rag_platform.domain.errors import NotFoundError, ValidationError

logger = structlog.get_logger(__name__)


def has_relevant_context(hits: list, threshold: float) -> bool:
    return bool(hits) and hits[0].score >= threshold


class Chat:
    def __init__(
        self,
        *,
        kb_repo: KnowledgeBaseRepository,
        query_repo: QueryRepository,
        retrieval: RetrievalEngine,
        reranker: RerankerProvider,
        llm: LlmProvider,
        observability: ChatObservability,
        llm_log: LlmRequestLogPort,
        resource_guard: ChatResourceGuard,
    ) -> None:
        self._kb_repo = kb_repo
        self._query_repo = query_repo
        self._retrieval = retrieval
        self._reranker = reranker
        self._llm = llm
        self._observability = observability
        self._llm_log = llm_log
        self._resource_guard = resource_guard

    async def execute(self, *, knowledge_base_id: UUID, question: str) -> ChatResult:
        started_total = time.perf_counter()
        kb = await self._kb_repo.get_by_id(knowledge_base_id)
        if kb is None:
            raise NotFoundError(f"knowledge base not found: {knowledge_base_id}")
        if not question.strip():
            raise ValidationError("question is required")
        settings = get_settings()
        if len(question) > settings.chat_max_question_chars:
            raise ValidationError("question exceeds maximum length")

        lease = await self._resource_guard.acquire(organization_id=kb.organization_id)
        reservation_id = await self._resource_guard.reserve_budget(
            organization_id=kb.organization_id,
            estimate_usd=settings.chat_max_request_cost_usd,
        )
        cost_usd = 0.0
        budget_settled = False
        try:
            safe_question = sanitize_user_question(question)
            self._observability.bind_chat_context(
                organization_id=str(kb.organization_id),
                knowledge_base_id=str(knowledge_base_id),
            )
            self._observability.inc_tenant_usage(str(kb.organization_id))
            now = datetime.now(tz=UTC)
            query = Query(
                id=uuid4(),
                knowledge_base_id=knowledge_base_id,
                organization_id=kb.organization_id,
                question=safe_question,
                status=QueryStatus.CREATED,
                answer=None,
                error_message=None,
                created_at=now,
                updated_at=now,
            )
            query = await self._query_repo.create(query)
            t0 = time.perf_counter()
            hits = await self._retrieval.retrieve(
                organization_id=kb.organization_id,
                knowledge_base_id=knowledge_base_id,
                question=safe_question,
                limit=settings.retrieval_top_k,
            )
            self._observability.observe_stage("retrieval", time.perf_counter() - t0)
            t1 = time.perf_counter()
            reranked = await self._reranker.rerank(safe_question, hits, settings.rerank_k)
            self._observability.observe_stage("rerank", time.perf_counter() - t1)
            await self._query_repo.replace_retrieval_results(query.id, knowledge_base_id, reranked)
            await self._query_repo.save(
                Query(
                    id=query.id,
                    knowledge_base_id=query.knowledge_base_id,
                    organization_id=query.organization_id,
                    question=query.question,
                    status=QueryStatus.RETRIEVED,
                    answer=query.answer,
                    error_message=query.error_message,
                    created_at=query.created_at,
                    updated_at=datetime.now(tz=UTC),
                ),
            )
            context, selected = build_context(reranked, settings.context_token_budget)
            if not selected or not has_relevant_context(reranked, settings.rag_min_relevance_score):
                insufficient = ChatResult(
                    query_id=query.id,
                    answer="Not enough indexed content to answer this question.",
                    citations=[],
                    insufficient_context=True,
                )
                await self._query_repo.save(
                    Query(
                        id=query.id,
                        knowledge_base_id=query.knowledge_base_id,
                        organization_id=query.organization_id,
                        question=query.question,
                        status=QueryStatus.COMPLETED,
                        answer=insufficient.answer,
                        error_message=None,
                        created_at=query.created_at,
                        updated_at=datetime.now(tz=UTC),
                    ),
                )
                self._observability.inc_chat_request(str(knowledge_base_id), "insufficient")
                self._observability.observe_chat_latency(time.perf_counter() - started_total)
                return insufficient
            user_prompt = f"Question: {safe_question}\n\nContext:\n{context}"
            started = time.perf_counter()
            try:
                completion = await asyncio.wait_for(
                    self._llm.complete(SYSTEM_PROMPT, user_prompt),
                    timeout=settings.llm_timeout_seconds,
                )
            except TimeoutError as exc:
                self._observability.inc_chat_request(str(knowledge_base_id), "timeout")
                raise ValidationError("llm timeout") from exc
            self._observability.observe_stage("llm", time.perf_counter() - started)
            latency_ms = int((time.perf_counter() - started) * 1000)
            if completion.text.strip().upper().startswith(INSUFFICIENT_CONTEXT):
                answer_text = "Not enough indexed content to answer this question."
                await self._query_repo.save(
                    Query(
                        id=query.id,
                        knowledge_base_id=query.knowledge_base_id,
                        organization_id=query.organization_id,
                        question=query.question,
                        status=QueryStatus.COMPLETED,
                        answer=answer_text,
                        error_message=None,
                        created_at=query.created_at,
                        updated_at=datetime.now(tz=UTC),
                    ),
                )
                self._observability.inc_chat_request(str(knowledge_base_id), "insufficient")
                self._observability.observe_chat_latency(time.perf_counter() - started_total)
                return ChatResult(
                    query_id=query.id,
                    answer=answer_text,
                    citations=[],
                    insufficient_context=True,
                )
            allowed = {str(hit.chunk_id) for hit in selected}
            citation_ids = validate_citations(completion.citation_chunk_ids, allowed)
            by_id = {str(hit.chunk_id): hit for hit in selected}
            citation_models = [
                Citation(
                    chunk_id=UUID(cid),
                    document_id=by_id[cid].document_id,
                    snippet=by_id[cid].content[:240],
                    page=by_id[cid].page,
                )
                for cid in citation_ids
            ]
            prompt_tokens = estimate_tokens(user_prompt) + estimate_tokens(SYSTEM_PROMPT)
            completion_tokens = estimate_tokens(completion.text)
            if completion_tokens > settings.chat_max_output_tokens:
                raise ValidationError("completion exceeds output token limit")
            self._observability.inc_tokens(prompt=prompt_tokens, completion=completion_tokens)
            cost_usd = (
                (prompt_tokens + completion_tokens) / 1000.0 * settings.llm_cost_per_1k_tokens_usd
            )
            await self._llm_log.record_completed(
                query_id=query.id,
                model=self._llm.model_name,
                prompt_version=PROMPT_VERSION,
                latency_ms=latency_ms,
                prompt_tokens=prompt_tokens,
                completion_tokens=completion_tokens,
                estimated_cost_usd=cost_usd,
            )
            await self._query_repo.save(
                Query(
                    id=query.id,
                    knowledge_base_id=query.knowledge_base_id,
                    organization_id=query.organization_id,
                    question=query.question,
                    status=QueryStatus.COMPLETED,
                    answer=completion.text,
                    error_message=None,
                    created_at=query.created_at,
                    updated_at=datetime.now(tz=UTC),
                ),
            )
            self._observability.inc_chat_request(str(knowledge_base_id), "ok")
            self._observability.observe_chat_latency(time.perf_counter() - started_total)
            logger.info("chat_completed", query_id=str(query.id), latency_ms=latency_ms)
            return ChatResult(
                query_id=query.id,
                answer=completion.text,
                citations=citation_models,
                insufficient_context=False,
            )
        except Exception:
            await self._resource_guard.release_budget(
                organization_id=kb.organization_id,
                reservation_id=reservation_id,
            )
            budget_settled = True
            raise
        finally:
            if not budget_settled:
                await self._resource_guard.settle_budget(
                    organization_id=kb.organization_id,
                    reservation_id=reservation_id,
                    actual_usd=cost_usd,
                )
            await lease.release()
