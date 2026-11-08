from typing import Annotated
from uuid import UUID

import structlog
from fastapi import APIRouter, Depends, File, Form, Query, UploadFile, status
from sqlalchemy.ext.asyncio import AsyncSession

from rag_platform.api.deps import get_db_session, get_object_storage
from rag_platform.api.deps_auth import verify_kb_tenant_scope
from rag_platform.api.deps_tenant import get_tenant_context
from rag_platform.api.schemas.documents import DocumentListResponse, DocumentResponse
from rag_platform.application.ports.storage import ObjectStorage
from rag_platform.composition.http import (
    build_create_document,
    build_delete_document,
    build_get_document,
    build_list_documents,
)
from rag_platform.domain.tenant import TenantContext

router = APIRouter(prefix="/documents", tags=["documents"])

_log = structlog.get_logger(__name__)


@router.get("", response_model=DocumentListResponse)
async def list_documents(
    knowledge_base_id: Annotated[UUID, Query()],
    session: Annotated[AsyncSession, Depends(get_db_session)],
    tenant: Annotated[TenantContext, Depends(get_tenant_context)],
) -> DocumentListResponse:
    await verify_kb_tenant_scope(knowledge_base_id, session, tenant)
    items = await build_list_documents(session).execute(knowledge_base_id=knowledge_base_id)
    return DocumentListResponse(
        items=[DocumentResponse.from_entity(doc) for doc in items],
    )


@router.get("/{document_id}", response_model=DocumentResponse)
async def get_document(
    document_id: UUID,
    knowledge_base_id: Annotated[UUID, Query()],
    session: Annotated[AsyncSession, Depends(get_db_session)],
    tenant: Annotated[TenantContext, Depends(get_tenant_context)],
) -> DocumentResponse:
    await verify_kb_tenant_scope(knowledge_base_id, session, tenant)
    document = await build_get_document(session).execute(
        document_id=document_id,
        knowledge_base_id=knowledge_base_id,
    )
    return DocumentResponse.from_entity(document)


@router.post("", status_code=status.HTTP_202_ACCEPTED, response_model=DocumentResponse)
async def upload_document(
    knowledge_base_id: Annotated[UUID, Form()],
    file: Annotated[UploadFile, File()],
    session: Annotated[AsyncSession, Depends(get_db_session)],
    storage: Annotated[ObjectStorage, Depends(get_object_storage)],
    tenant: Annotated[TenantContext, Depends(get_tenant_context)],
) -> DocumentResponse:
    await verify_kb_tenant_scope(knowledge_base_id, session, tenant)
    content = await file.read()
    document = await build_create_document(session, storage).execute(
        knowledge_base_id=knowledge_base_id,
        filename=file.filename or "upload.bin",
        mime_type=file.content_type or "application/octet-stream",
        content=content,
    )
    return DocumentResponse.from_entity(document)


@router.delete("/{document_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_document(
    document_id: UUID,
    knowledge_base_id: Annotated[UUID, Query()],
    session: Annotated[AsyncSession, Depends(get_db_session)],
    tenant: Annotated[TenantContext, Depends(get_tenant_context)],
) -> None:
    await verify_kb_tenant_scope(knowledge_base_id, session, tenant)
    await build_delete_document(session).execute(
        document_id=document_id,
        knowledge_base_id=knowledge_base_id,
    )
