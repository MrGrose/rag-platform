from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from rag_platform.api.deps import get_db_session
from rag_platform.api.deps_auth import verify_kb_tenant_scope
from rag_platform.api.deps_tenant import get_tenant_context
from rag_platform.api.schemas.queries import QueryResponse
from rag_platform.composition.http import build_get_query
from rag_platform.domain.tenant import TenantContext

router = APIRouter(prefix="/queries", tags=["queries"])


@router.get("/{query_id}", response_model=QueryResponse)
async def get_query(
    query_id: UUID,
    knowledge_base_id: Annotated[UUID, Query()],
    session: Annotated[AsyncSession, Depends(get_db_session)],
    tenant: Annotated[TenantContext, Depends(get_tenant_context)],
) -> QueryResponse:
    await verify_kb_tenant_scope(knowledge_base_id, session, tenant)
    query, hits = await build_get_query(session).execute(
        query_id=query_id,
        knowledge_base_id=knowledge_base_id,
        organization_id=tenant.organization_id,
    )
    return QueryResponse.from_entity(query, hits)
