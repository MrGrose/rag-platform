from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from rag_platform.api.deps import get_db_session
from rag_platform.api.deps_auth import verify_kb_tenant_scope
from rag_platform.api.deps_tenant import get_tenant_context
from rag_platform.api.schemas.chat import ChatRequest, ChatResponse
from rag_platform.composition.http import build_chat
from rag_platform.domain.tenant import TenantContext

router = APIRouter(prefix="/chat", tags=["chat"])


@router.post("", response_model=ChatResponse)
async def chat(
    body: ChatRequest,
    session: Annotated[AsyncSession, Depends(get_db_session)],
    tenant: Annotated[TenantContext, Depends(get_tenant_context)],
) -> ChatResponse:
    await verify_kb_tenant_scope(body.knowledge_base_id, session, tenant)
    use_case = await build_chat(session, body.knowledge_base_id)
    result = await use_case.execute(
        knowledge_base_id=body.knowledge_base_id,
        question=body.question,
    )
    return ChatResponse.from_result(result)
