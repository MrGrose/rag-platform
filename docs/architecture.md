# Architecture overview

RAG Platform is a multi-tenant HTTP API for knowledge bases: upload documents, index them asynchronously, and answer questions with retrieved context and citations.

## Components

| Component | Role |
|-----------|------|
| **API** (`uvicorn`) | REST v1: documents, chat, queries, evaluations; health and metrics |
| **Worker** (`arq`) | Background indexing: parse, chunk, embed, store vectors |
| **PostgreSQL + pgvector** | Metadata, chunks, embeddings, query history |
| **Redis** | Job queue and caching |
| **S3-compatible storage** | Raw document blobs (MinIO in local compose) |

## Request flow (chat)

1. Client sends `POST /v1/chat` with `knowledge_base_id` and message.
2. API validates org scope, preprocesses the query, runs hybrid retrieval (vector + keyword).
3. Optional rerank, context assembly, LLM generation with citation checks.
4. Response includes answer text and source references.

## Ingestion flow

1. `POST /v1/documents` stores the file in object storage and enqueues processing.
2. Worker parses (PDF/text), chunks, embeds, writes rows to Postgres.
3. Document status moves through `pending` → `processing` → `ready` or `failed`.

## Code layout

Application code lives under `src/rag_platform/`:

- `api/` — HTTP transport and schemas only
- `application/` — use cases, ports, retrieval and prompt logic
- `domain/` — entities and domain errors
- `infrastructure/` — SQLAlchemy, S3, Redis, providers
- `workers/` — ARQ task entrypoints

Indexing and provider calls do not run on the API request path for uploads; they run in the worker.

## Providers

Embedding, LLM, and reranker backends are selected via environment variables. CI and the default local setup use in-process fake providers; production setups typically point at Ollama, OpenAI-compatible APIs, or other configured endpoints (see [configuration](configuration.md)).
