from prometheus_client import CONTENT_TYPE_LATEST, Counter, Gauge, Histogram, generate_latest

CHAT_REQUESTS = Counter(
    "rag_chat_requests_total",
    "Chat requests",
    ["knowledge_base_id", "status"],
)
CHAT_LATENCY = Histogram(
    "rag_chat_latency_seconds",
    "Chat end-to-end latency",
    buckets=(0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0),
)
STAGE_LATENCY = Histogram(
    "rag_stage_latency_seconds",
    "Pipeline stage latency",
    ["stage"],
)
TENANT_USAGE = Counter(
    "rag_tenant_requests_total",
    "Requests per organization",
    ["organization_id"],
)
PROMPT_TOKENS = Counter("rag_llm_prompt_tokens_total", "Estimated prompt tokens")
COMPLETION_TOKENS = Counter("rag_llm_completion_tokens_total", "Estimated completion tokens")
CHAT_CONCURRENCY_REJECTED = Counter(
    "rag_chat_concurrency_rejected_total",
    "Chat requests rejected by concurrency guard",
    ["scope"],
)
CHAT_BUDGET_EXCEEDED = Counter(
    "rag_chat_budget_exceeded_total",
    "Chat requests blocked by budget guard",
    ["reason"],
)
CHAT_ACTIVE_REQUESTS = Gauge("rag_chat_active_requests", "Active chat requests")


def metrics_body() -> tuple[bytes, str]:
    return generate_latest(), CONTENT_TYPE_LATEST
