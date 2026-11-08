# RAG Platform

Multi-tenant retrieval-augmented generation API: document ingestion, hybrid search, and grounded chat with citations.

**Stack:** FastAPI · PostgreSQL (pgvector) · Redis · ARQ · S3-compatible storage · optional Ollama / OpenAI-compatible providers.

## Features

- Knowledge bases scoped by organization
- PDF and plain-text upload with async indexing
- Hybrid vector + keyword retrieval, optional reranking
- Chat with citation validation
- Prometheus metrics and structured logging

## Quick start

```bash
cp .env.example .env
docker compose up -d
uv sync
uv run alembic upgrade head
uv run uvicorn rag_platform.api.app:app --reload --port 8000
```

Worker (separate terminal):

```bash
uv run arq rag_platform.workers.settings.WorkerSettings
```

OpenAPI: `http://localhost:8000/docs`

## Tests

```bash
uv sync --group dev
docker compose up -d
uv run alembic upgrade head
uv run pytest -q
```

## Documentation

| Doc | Description |
|-----|-------------|
| [API](docs/api.md) | v1 routes, headers, examples |
| [Configuration](docs/configuration.md) | Environment variables |
| [Architecture](docs/architecture.md) | Components and data flows |

## Project layout

| Path | Role |
|------|------|
| `src/rag_platform/api` | HTTP routers and middleware |
| `src/rag_platform/application` | Use cases and ports |
| `src/rag_platform/infrastructure` | DB, S3, Redis, providers |
| `src/rag_platform/workers` | ARQ tasks |
| `alembic/` | Schema migrations |
| `tests/` | Unit, integration, RAG checks |

## Limitations

- JWT authentication is not implemented; API key + organization header when `API_KEY` is set.
- Default compose uses development credentials and fake LLM/embeddings in CI.
- Not hardened for production without your own secrets, TLS, and provider configuration.
