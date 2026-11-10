# API overview

Base path: `/v1/*` (except `/health`, `/ready`, `/metrics`).

## Authentication

Production:

- Header **`X-API-Key`**: tenant key `rk_{prefix}_{secret}` (organization comes from the key record).
- Optional **`X-Organization-Id`**: must match the key’s organization when both are sent; it must not be the sole tenant identity when `ALLOW_OPEN_API=false`.

Development (`ALLOW_OPEN_API=true`): `X-Organization-Id` only (no key).

Legacy bootstrap only: `ALLOW_LEGACY_GLOBAL_API_KEY=true` + shared `API_KEY` (not for multi-tenant production).

Key lifecycle CLI: `python -m rag_platform.cli.manage_api_keys create|list|revoke`.

## Endpoints

| Method | Path | Description |
|--------|------|-------------|
| POST | `/v1/documents` | Upload; `202` + processing |
| GET | `/v1/documents` | List documents |
| GET | `/v1/documents/{id}` | Document detail |
| DELETE | `/v1/documents/{id}` | Soft delete + cleanup job |
| POST | `/v1/chat` | Sync RAG answer + citations (concurrency/budget limits) |
| GET | `/v1/queries/{id}` | Query and retrieval audit |
| POST | `/v1/extract` | Structured facts from an indexed document, with quote citations |
| POST | `/v1/evaluations` | Create evaluation + outbox event (`202`, `pending`) |
| GET | `/v1/evaluations/{id}` | Evaluation status/results |
| GET | `/health` | Liveness |
| GET | `/ready` | Dependency readiness |

## Chat limits (HTTP errors)

- `409` — concurrency or budget guard (`ConflictError`).
- `503` — Redis guard unavailable when `RATE_LIMIT_FAIL_CLOSED=true`.
- `422` — question/output validation.

## Evaluations

`POST /v1/evaluations` commits the evaluation row and an outbox event atomically. A worker dispatches to ARQ (at-least-once; worker is idempotent for completed runs).

OpenAPI: FastAPI app at runtime.

## Extraction

`POST /v1/extract` builds JSON from an already indexed document: parties, dates, amounts, obligations, risks, decisions and owners. Every fact carries the quote the model copied and the chunk it came from. Fields the document does not state are listed in `missing`.

```json
{
  "knowledge_base_id": "00000000-0000-4000-8000-000000000002",
  "document_id": "3d0f9c1e-6d43-4d1f-9c2e-5a3b7c9d1e2f"
}
```

The endpoint requires a non-fake LLM provider and returns `503` otherwise. Large documents are truncated at 24,000 characters and the response sets `truncated`. Citations point to the chunk index and include `page` when the parser reports page boundaries (PDF does, plain text is page 1).
