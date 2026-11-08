from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query, status
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from rag_platform.api.deps import get_db_session
from rag_platform.api.deps_auth import verify_kb_tenant_scope
from rag_platform.api.deps_tenant import get_tenant_context
from rag_platform.composition.http import build_get_evaluation, build_start_evaluation
from rag_platform.domain.tenant import TenantContext

router = APIRouter(prefix="/evaluations", tags=["evaluations"])


class EvaluationCreateRequest(BaseModel):
    knowledge_base_id: UUID


class EvaluationResponse(BaseModel):
    id: UUID
    status: str
    metrics_json: str | None


@router.post("", status_code=status.HTTP_202_ACCEPTED, response_model=EvaluationResponse)
async def create_evaluation(
    body: EvaluationCreateRequest,
    session: Annotated[AsyncSession, Depends(get_db_session)],
    tenant: Annotated[TenantContext, Depends(get_tenant_context)],
) -> EvaluationResponse:
    organization_id = await verify_kb_tenant_scope(body.knowledge_base_id, session, tenant)
    record = await build_start_evaluation(session).execute(
        knowledge_base_id=body.knowledge_base_id,
        organization_id=organization_id,
    )
    return EvaluationResponse(
        id=record.id,
        status=record.status,
        metrics_json=record.metrics_json,
    )


@router.get("/{evaluation_id}", response_model=EvaluationResponse)
async def get_evaluation(
    evaluation_id: UUID,
    knowledge_base_id: Annotated[UUID, Query()],
    session: Annotated[AsyncSession, Depends(get_db_session)],
    tenant: Annotated[TenantContext, Depends(get_tenant_context)],
) -> EvaluationResponse:
    await verify_kb_tenant_scope(knowledge_base_id, session, tenant)
    record = await build_get_evaluation(session).execute(
        evaluation_id=evaluation_id,
        knowledge_base_id=knowledge_base_id,
        organization_id=tenant.organization_id,
    )
    return EvaluationResponse(
        id=record.id,
        status=record.status,
        metrics_json=record.metrics_json,
    )
