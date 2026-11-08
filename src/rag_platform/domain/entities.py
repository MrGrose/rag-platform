from dataclasses import dataclass
from datetime import datetime
from uuid import UUID

from rag_platform.domain.enums import DocumentStatus, QueryStatus


@dataclass(frozen=True, slots=True)
class Organization:
    id: UUID
    name: str
    created_at: datetime
    updated_at: datetime


@dataclass(frozen=True, slots=True)
class KnowledgeBase:
    id: UUID
    organization_id: UUID
    name: str
    created_at: datetime
    updated_at: datetime


@dataclass(frozen=True, slots=True)
class DocumentChunk:
    id: UUID
    document_id: UUID
    knowledge_base_id: UUID
    organization_id: UUID
    chunk_index: int
    content: str
    embedding: list[float]
    token_count: int
    created_at: datetime
    updated_at: datetime


@dataclass(frozen=True, slots=True)
class Document:
    id: UUID
    knowledge_base_id: UUID
    organization_id: UUID
    filename: str
    mime_type: str
    size_bytes: int
    status: DocumentStatus
    storage_key: str
    content_hash: str
    content_version: int
    error_message: str | None
    deleted_at: datetime | None
    created_at: datetime
    updated_at: datetime
    processing_started_at: datetime | None = None


@dataclass(frozen=True, slots=True)
class Query:
    id: UUID
    knowledge_base_id: UUID
    organization_id: UUID
    question: str
    status: QueryStatus
    answer: str | None
    error_message: str | None
    created_at: datetime
    updated_at: datetime


@dataclass(frozen=True, slots=True)
class RetrievalHit:
    chunk_id: UUID
    document_id: UUID
    knowledge_base_id: UUID
    content: str
    score: float
    rank: int


@dataclass(frozen=True, slots=True)
class Citation:
    chunk_id: UUID
    document_id: UUID
    snippet: str


@dataclass(frozen=True, slots=True)
class ChatResult:
    query_id: UUID
    answer: str
    citations: list[Citation]
    insufficient_context: bool


@dataclass(frozen=True, slots=True)
class EvaluationRecord:
    id: UUID
    status: str
    metrics_json: str | None
    lease_expires_at: datetime | None = None
