from functools import lru_cache
from typing import Self

from pydantic import Field, PostgresDsn, RedisDsn, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    app_env: str = Field(default="development", alias="APP_ENV")
    log_level: str = Field(default="INFO", alias="LOG_LEVEL")
    database_url: PostgresDsn = Field(
        default="postgresql+asyncpg://rag:rag@localhost:5436/rag",
        alias="DATABASE_URL",
    )
    redis_url: RedisDsn = Field(default="redis://localhost:6380/0", alias="REDIS_URL")
    arq_redis_url: RedisDsn = Field(default="redis://localhost:6380/1", alias="ARQ_REDIS_URL")
    s3_endpoint_url: str = Field(default="http://localhost:9000", alias="S3_ENDPOINT_URL")
    s3_access_key: str = Field(default="minioadmin", alias="S3_ACCESS_KEY")
    s3_secret_key: str = Field(default="minioadmin", alias="S3_SECRET_KEY")
    s3_bucket: str = Field(default="rag-documents", alias="S3_BUCKET")
    embeddings_provider: str = Field(default="fake", alias="EMBEDDINGS_PROVIDER")
    embeddings_model: str = Field(default="BAAI/bge-m3", alias="EMBEDDINGS_MODEL")
    embeddings_device: str = Field(default="cpu", alias="EMBEDDINGS_DEVICE")
    embeddings_batch_size: int = Field(default=16, alias="EMBEDDINGS_BATCH_SIZE")
    reranker_provider: str = Field(default="fake", alias="RERANKER_PROVIDER")
    reranker_model: str = Field(default="BAAI/bge-reranker-v2-m3", alias="RERANKER_MODEL")
    llm_provider: str = Field(default="fake", alias="LLM_PROVIDER")
    llm_base_url: str = Field(default="https://api.deepseek.com/v1", alias="LLM_BASE_URL")
    llm_api_key: str = Field(default="", alias="LLM_API_KEY")
    llm_model: str = Field(default="deepseek-chat", alias="LLM_MODEL")
    llm_temperature: float = Field(default=0.0, alias="LLM_TEMPERATURE")
    llm_max_retries: int = Field(default=2, alias="LLM_MAX_RETRIES")
    rag_min_relevance_score: float = Field(default=0.2, alias="RAG_MIN_RELEVANCE_SCORE")
    retrieval_mode: str = Field(default="hybrid", alias="RETRIEVAL_MODE")
    retrieval_top_k: int = Field(default=20, alias="RETRIEVAL_TOP_K")
    rerank_k: int = Field(default=10, alias="RERANK_K")
    context_token_budget: int = Field(default=2000, alias="CONTEXT_TOKEN_BUDGET")
    llm_timeout_seconds: float = Field(default=30.0, alias="LLM_TIMEOUT_SECONDS")
    chat_max_question_chars: int = Field(default=4000, alias="CHAT_MAX_QUESTION_CHARS")
    chat_max_output_tokens: int = Field(default=1024, alias="CHAT_MAX_OUTPUT_TOKENS")
    processing_stale_seconds: int = Field(default=900, alias="PROCESSING_STALE_SECONDS")
    api_key: str = Field(default="", alias="API_KEY")
    api_key_hash_pepper: str = Field(default="", alias="API_KEY_HASH_PEPPER")
    allow_open_api: bool = Field(default=False, alias="ALLOW_OPEN_API")
    allow_fake_providers: bool = Field(default=True, alias="ALLOW_FAKE_PROVIDERS")
    allow_legacy_global_api_key: bool = Field(default=False, alias="ALLOW_LEGACY_GLOBAL_API_KEY")
    rate_limit_per_minute: int = Field(default=120, alias="RATE_LIMIT_PER_MINUTE")
    rate_limit_fail_closed: bool = Field(default=False, alias="RATE_LIMIT_FAIL_CLOSED")
    llm_cost_per_1k_tokens_usd: float = Field(default=0.002, alias="LLM_COST_PER_1K_TOKENS_USD")
    chat_global_concurrency: int = Field(default=32, alias="CHAT_GLOBAL_CONCURRENCY")
    chat_org_concurrency: int = Field(default=8, alias="CHAT_ORG_CONCURRENCY")
    chat_concurrency_lease_seconds: int = Field(default=120, alias="CHAT_CONCURRENCY_LEASE_SECONDS")
    chat_max_request_cost_usd: float = Field(default=0.25, alias="CHAT_MAX_REQUEST_COST_USD")
    chat_daily_org_budget_usd: float = Field(default=25.0, alias="CHAT_DAILY_ORG_BUDGET_USD")
    outbox_batch_size: int = Field(default=20, alias="OUTBOX_BATCH_SIZE")
    outbox_max_attempts: int = Field(default=8, alias="OUTBOX_MAX_ATTEMPTS")
    outbox_lease_seconds: int = Field(default=60, alias="OUTBOX_LEASE_SECONDS")
    outbox_base_backoff_seconds: int = Field(default=5, alias="OUTBOX_BASE_BACKOFF_SECONDS")
    evaluation_lease_seconds: int = Field(default=900, alias="EVALUATION_LEASE_SECONDS")
    evaluation_recovery_batch_size: int = Field(default=20, alias="EVALUATION_RECOVERY_BATCH_SIZE")

    @model_validator(mode="after")
    def enforce_environment_policy(self) -> Self:
        env = self.app_env.strip().lower()
        if env == "test":
            return self
        if env == "production":
            violations: list[str] = []
            if self.allow_open_api:
                violations.append("ALLOW_OPEN_API must be false when APP_ENV=production")
            if not self.api_key_hash_pepper.strip():
                violations.append("API_KEY_HASH_PEPPER is required when APP_ENV=production")
            if not self.rate_limit_fail_closed:
                violations.append("RATE_LIMIT_FAIL_CLOSED must be true when APP_ENV=production")
            if self.allow_fake_providers:
                violations.append("ALLOW_FAKE_PROVIDERS must be false when APP_ENV=production")
            for name in ("embeddings_provider", "reranker_provider", "llm_provider"):
                if getattr(self, name).strip().lower() == "fake":
                    violations.append(f"{name.upper()} must not be fake when APP_ENV=production")
            if self.llm_provider.strip().lower() != "fake" and not self.llm_api_key.strip():
                violations.append("LLM_API_KEY is required for a non-fake LLM provider")
            if self.allow_legacy_global_api_key:
                violations.append("ALLOW_LEGACY_GLOBAL_API_KEY must be false in production")
            if violations:
                raise ValueError("; ".join(violations))
        return self


@lru_cache
def get_settings() -> Settings:
    return Settings()
