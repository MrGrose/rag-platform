from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from rag_platform.domain.errors import NotFoundError, ValidationError
from rag_platform.domain.tenant import TenantContext
from rag_platform.infrastructure.db.repositories import SqlAlchemyKnowledgeBaseRepository


async def verify_kb_tenant_scope(
    knowledge_base_id: UUID,
    session: AsyncSession,
    tenant: TenantContext,
) -> UUID:
    kb = await SqlAlchemyKnowledgeBaseRepository(session).get_by_id(knowledge_base_id)
    if kb is None:
        raise NotFoundError(f"knowledge base not found: {knowledge_base_id}")

    if kb.organization_id != tenant.organization_id:
        raise ValidationError("organization scope mismatch")

    return tenant.organization_id
