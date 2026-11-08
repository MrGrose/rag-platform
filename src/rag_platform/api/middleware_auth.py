from collections.abc import Awaitable, Callable

import structlog
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse, Response

from rag_platform.application.auth.resolve_tenant_api_key import TenantApiKeyAuthentication
from rag_platform.config import get_settings
from rag_platform.infrastructure.db.api_key_repository import SqlAlchemyApiKeyRepository
from rag_platform.infrastructure.db.session import session_scope

_PUBLIC_PATHS = {"/health", "/ready", "/metrics"}


class ApiKeyAuthMiddleware(BaseHTTPMiddleware):
    async def dispatch(
        self,
        request: Request,
        call_next: Callable[[Request], Awaitable[Response]],
    ) -> Response:
        settings = get_settings()
        if request.url.path in _PUBLIC_PATHS:
            return await call_next(request)

        if settings.allow_open_api:
            request.state.tenant = None
            return await call_next(request)

        if (
            settings.allow_legacy_global_api_key
            and settings.api_key
            and request.headers.get("X-API-Key", "") == settings.api_key
        ):
            request.state.tenant = None
            return await call_next(request)

        provided = request.headers.get("X-API-Key", "").strip()
        if not provided:
            return JSONResponse(status_code=401, content={"detail": "unauthorized"})

        if not settings.api_key_hash_pepper.strip():
            return JSONResponse(
                status_code=503,
                content={"detail": "API key authentication is not configured"},
            )

        async with session_scope() as session:
            auth = TenantApiKeyAuthentication(
                api_keys=SqlAlchemyApiKeyRepository(session),
                pepper=settings.api_key_hash_pepper,
            )
            tenant = await auth.authenticate(provided)
            await session.commit()

        if tenant is None:
            return JSONResponse(status_code=401, content={"detail": "unauthorized"})

        request.state.tenant = tenant
        structlog.contextvars.bind_contextvars(
            organization_id=str(tenant.organization_id),
            api_key_id=str(tenant.api_key_id),
        )
        return await call_next(request)
