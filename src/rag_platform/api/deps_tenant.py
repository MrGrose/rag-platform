from uuid import UUID

from fastapi import Header, Request

from rag_platform.config import get_settings
from rag_platform.domain.errors import ValidationError
from rag_platform.domain.tenant import TenantContext


def get_tenant_context(
    request: Request,
    x_organization_id: str | None = Header(default=None, alias="X-Organization-Id"),
) -> TenantContext:
    tenant = getattr(request.state, "tenant", None)
    if isinstance(tenant, TenantContext):
        if x_organization_id:
            try:
                header_org = UUID(x_organization_id)
            except ValueError as exc:
                raise ValidationError("invalid X-Organization-Id") from exc
            if header_org != tenant.organization_id:
                raise ValidationError("organization scope mismatch")
        return tenant

    settings = get_settings()
    if not settings.allow_open_api:
        raise ValidationError("unauthorized")

    if not x_organization_id:
        raise ValidationError("X-Organization-Id is required in open development mode")

    try:
        org = UUID(x_organization_id)
    except ValueError as exc:
        raise ValidationError("invalid X-Organization-Id") from exc

    return TenantContext(
        organization_id=org,
        api_key_id=None,
        scopes=("*",),
        auth_mode="open_dev",
    )
