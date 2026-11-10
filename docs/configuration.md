# Configuration

Environment-driven [Pydantic settings](../src/rag_platform/config/settings.py). Copy `.env.example` to `.env` locally.

## Core

| Variable | Purpose |
|----------|---------|
| `DATABASE_URL` | async SQLAlchemy URL (default `postgresql+asyncpg://rag:rag@localhost:5436/rag`) |
| `REDIS_URL` | Redis for ARQ, rate limit, chat guards, cache |
| `ARQ_REDIS_URL` | ARQ queue DB index |

## Security

| Variable | Default | Purpose |
|----------|---------|---------|
| `APP_ENV` | `development` | `production` enforces policy below |
| `API_KEY_HASH_PEPPER` | empty | **Required in production** — HMAC pepper for tenant API keys |
| `ALLOW_OPEN_API` | `false` | Dev-only: tenant via `X-Organization-Id` |
| `ALLOW_LEGACY_GLOBAL_API_KEY` | `false` | Bootstrap shared `API_KEY` (not multi-tenant) |
| `API_KEY` | empty | Legacy global key when legacy mode enabled |
| `RATE_LIMIT_FAIL_CLOSED` | `false` | `true` in production — 503 if Redis down |
| `RATE_LIMIT_PER_MINUTE` | 120 | Per-IP HTTP limit |

## Chat resource guards

| Variable | Purpose |
|----------|---------|
| `CHAT_GLOBAL_CONCURRENCY` | Max parallel chat requests (all tenants) |
| `CHAT_ORG_CONCURRENCY` | Per-organization parallel chat cap |
| `CHAT_CONCURRENCY_LEASE_SECONDS` | Redis slot TTL / stale recovery |
| `CHAT_MAX_QUESTION_CHARS` | Input size cap |
| `CHAT_MAX_OUTPUT_TOKENS` | Estimated completion cap |
| `CHAT_MAX_REQUEST_COST_USD` | Per-request budget reservation |
| `CHAT_DAILY_ORG_BUDGET_USD` | Daily org spend guard (estimate) |

## Outbox dispatcher

| Variable | Purpose |
|----------|---------|
| `OUTBOX_POLL_BATCH_SIZE` | Events claimed per tick |
| `OUTBOX_MAX_ATTEMPTS` | Dead-letter threshold |
| `OUTBOX_LOCK_SECONDS` | Claim lease |

## Providers

| Variable | Default | Purpose |
|----------|---------|---------|
| `EMBEDDINGS_PROVIDER` | `fake` | `fake` or `bge_m3` |
| `EMBEDDINGS_MODEL` | `BAAI/bge-m3` | sentence-transformers model, 1024 dims |
| `EMBEDDINGS_DEVICE` | `cpu` | `cpu` or `cuda` |
| `EMBEDDINGS_BATCH_SIZE` | 16 | encode batch size |
| `RERANKER_PROVIDER` | `fake` | `fake` or `bge_reranker` |
| `RERANKER_MODEL` | `BAAI/bge-reranker-v2-m3` | cross-encoder model |
| `LLM_PROVIDER` | `fake` | `fake` or `openai` (OpenAI-compatible endpoint) |
| `LLM_BASE_URL` | `https://api.deepseek.com/v1` | chat completions base URL |
| `LLM_API_KEY` | empty | required for a non-fake LLM |
| `LLM_MODEL` | `deepseek-chat` | model name passed through |
| `LLM_MAX_RETRIES` | 2 | retries on 429, 5xx, network errors |

`bge_m3` and `bge_reranker` need the optional extra: `uv sync --extra local`.
In production all three providers must be non-fake, and `ALLOW_FAKE_PROVIDERS` must be false.

## Retrieval / chat quality

| Variable | Purpose |
|----------|---------|
| `RETRIEVAL_TOP_K` | hybrid retrieval limit |
| `RERANK_K` | reranker top results |
| `CONTEXT_TOKEN_BUDGET` | context builder budget |
| `LLM_TIMEOUT_SECONDS` | chat generation timeout |
| `LLM_COST_PER_1K_TOKENS_USD` | estimated cost on `llm_requests` |
| `RAG_MIN_RELEVANCE_SCORE` | top reranked score below which chat refuses without an LLM call |

## Processing

| Variable | Purpose |
|----------|---------|
| `PROCESSING_STALE_SECONDS` | reclaim stuck `processing` documents |

## Object storage

S3 endpoint, bucket, and credentials via settings (see `.env.example`). Secrets must never be committed.
