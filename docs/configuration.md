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

## Retrieval / chat quality

| Variable | Purpose |
|----------|---------|
| `RETRIEVAL_TOP_K` | hybrid retrieval limit |
| `RERANK_K` | reranker top results |
| `CONTEXT_TOKEN_BUDGET` | context builder budget |
| `LLM_TIMEOUT_SECONDS` | chat generation timeout |
| `LLM_COST_PER_1K_TOKENS_USD` | estimated cost on `llm_requests` |

## Processing

| Variable | Purpose |
|----------|---------|
| `PROCESSING_STALE_SECONDS` | reclaim stuck `processing` documents |

## Object storage

S3 endpoint, bucket, and credentials via settings (see `.env.example`). Secrets must never be committed.
