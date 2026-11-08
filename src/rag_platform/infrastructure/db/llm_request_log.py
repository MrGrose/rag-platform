from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from rag_platform.application.ports.llm_requests import LlmRequestLogPort
from rag_platform.infrastructure.db.models import LlmRequestModel


class SqlAlchemyLlmRequestLog(LlmRequestLogPort):
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def record_completed(
        self,
        *,
        query_id: UUID,
        model: str,
        prompt_version: str,
        latency_ms: int,
        prompt_tokens: int,
        completion_tokens: int,
        estimated_cost_usd: float,
    ) -> None:
        self._session.add(
            LlmRequestModel(
                query_id=query_id,
                model=model,
                prompt_version=prompt_version,
                latency_ms=latency_ms,
                status="completed",
                prompt_tokens=prompt_tokens,
                completion_tokens=completion_tokens,
                estimated_cost_usd=estimated_cost_usd,
            ),
        )
        await self._session.flush()
