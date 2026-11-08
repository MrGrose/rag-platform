from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field

from rag_platform.domain.entities import Document


class DocumentResponse(BaseModel):
    id: UUID
    knowledge_base_id: UUID
    organization_id: UUID
    filename: str
    mime_type: str
    size_bytes: int
    status: str
    content_hash: str
    content_version: int
    error_message: str | None = None
    created_at: datetime
    updated_at: datetime

    @classmethod
    def from_entity(cls, document: Document) -> "DocumentResponse":
        return cls(
            id=document.id,
            knowledge_base_id=document.knowledge_base_id,
            organization_id=document.organization_id,
            filename=document.filename,
            mime_type=document.mime_type,
            size_bytes=document.size_bytes,
            status=str(document.status),
            content_hash=document.content_hash,
            content_version=document.content_version,
            error_message=document.error_message,
            created_at=document.created_at,
            updated_at=document.updated_at,
        )


class DocumentListResponse(BaseModel):
    items: list[DocumentResponse] = Field(default_factory=list)
