import structlog

from rag_platform.application.ports.observability import ChatObservability
from rag_platform.infrastructure.metrics import (
    CHAT_LATENCY,
    CHAT_REQUESTS,
    COMPLETION_TOKENS,
    PROMPT_TOKENS,
    STAGE_LATENCY,
    TENANT_USAGE,
)

logger = structlog.get_logger(__name__)


class PrometheusChatObservability(ChatObservability):
    def bind_chat_context(self, organization_id: str, knowledge_base_id: str) -> None:
        structlog.contextvars.bind_contextvars(
            organization_id=organization_id,
            knowledge_base_id=knowledge_base_id,
        )

    def inc_tenant_usage(self, organization_id: str) -> None:
        TENANT_USAGE.labels(organization_id=organization_id).inc()

    def observe_stage(self, stage: str, seconds: float) -> None:
        STAGE_LATENCY.labels(stage=stage).observe(seconds)

    def inc_chat_request(self, knowledge_base_id: str, status: str) -> None:
        CHAT_REQUESTS.labels(knowledge_base_id=knowledge_base_id, status=status).inc()

    def observe_chat_latency(self, seconds: float) -> None:
        CHAT_LATENCY.observe(seconds)

    def inc_tokens(self, *, prompt: int, completion: int) -> None:
        PROMPT_TOKENS.inc(prompt)
        COMPLETION_TOKENS.inc(completion)
