from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from rag_platform.api.deps import get_db_session
from rag_platform.api.deps_auth import verify_kb_tenant_scope
from rag_platform.api.deps_tenant import get_tenant_context
from rag_platform.composition.http import build_extract_facts
from rag_platform.domain.tenant import TenantContext

router = APIRouter(prefix="/extract", tags=["extract"])


class ExtractRequest(BaseModel):
    knowledge_base_id: UUID
    document_id: UUID


class ExtractedFactResponse(BaseModel):
    text: str
    quote: str


class FactCitationResponse(BaseModel):
    field: str
    chunk_id: UUID | None
    chunk_index: int | None
    quote: str
    page: int | None = None


class ExtractResponse(BaseModel):
    document_id: UUID
    parties: list[ExtractedFactResponse] = Field(default_factory=list)
    dates: list[ExtractedFactResponse] = Field(default_factory=list)
    amounts: list[ExtractedFactResponse] = Field(default_factory=list)
    obligations: list[ExtractedFactResponse] = Field(default_factory=list)
    risks: list[ExtractedFactResponse] = Field(default_factory=list)
    decisions: list[ExtractedFactResponse] = Field(default_factory=list)
    owners: list[ExtractedFactResponse] = Field(default_factory=list)
    missing: list[str] = Field(default_factory=list)
    citations: list[FactCitationResponse] = Field(default_factory=list)
    truncated: bool = False


@router.post("", response_model=ExtractResponse)
async def extract_facts(
    body: ExtractRequest,
    session: Annotated[AsyncSession, Depends(get_db_session)],
    tenant: Annotated[TenantContext, Depends(get_tenant_context)],
) -> ExtractResponse:
    await verify_kb_tenant_scope(body.knowledge_base_id, session, tenant)
    result = await build_extract_facts(session).execute(
        knowledge_base_id=body.knowledge_base_id,
        document_id=body.document_id,
    )
    payload = result.payload
    return ExtractResponse(
        document_id=result.document_id,
        parties=[ExtractedFactResponse(**fact.model_dump()) for fact in payload.parties],
        dates=[ExtractedFactResponse(**fact.model_dump()) for fact in payload.dates],
        amounts=[ExtractedFactResponse(**fact.model_dump()) for fact in payload.amounts],
        obligations=[ExtractedFactResponse(**fact.model_dump()) for fact in payload.obligations],
        risks=[ExtractedFactResponse(**fact.model_dump()) for fact in payload.risks],
        decisions=[ExtractedFactResponse(**fact.model_dump()) for fact in payload.decisions],
        owners=[ExtractedFactResponse(**fact.model_dump()) for fact in payload.owners],
        missing=result.missing,
        citations=[
            FactCitationResponse(
                field=citation.field,
                chunk_id=citation.chunk_id,
                chunk_index=citation.chunk_index,
                quote=citation.quote,
                page=citation.page,
            )
            for citation in result.citations
        ],
        truncated=result.truncated,
    )
