from typing import Protocol
from uuid import UUID


class LlmRequestLogPort(Protocol):
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
    ) -> None: ...
