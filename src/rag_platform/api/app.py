from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI

from rag_platform.api.constants import API_PREFIX
from rag_platform.api.exceptions import domain_error_handler
from rag_platform.api.middleware import RequestIdMiddleware
from rag_platform.api.middleware_auth import ApiKeyAuthMiddleware
from rag_platform.api.middleware_rate_limit import RateLimitMiddleware
from rag_platform.api.routers import health, metrics, v1
from rag_platform.domain.errors import DomainError
from rag_platform.infrastructure.logging import configure_logging

__all__ = ["API_PREFIX", "app", "create_app"]


@asynccontextmanager
async def lifespan(_app: FastAPI) -> AsyncIterator[None]:
    configure_logging()
    yield


def create_app() -> FastAPI:
    app = FastAPI(title="RAG Platform", version="0.1.0", lifespan=lifespan)
    app.add_middleware(RateLimitMiddleware)
    app.add_middleware(ApiKeyAuthMiddleware)
    app.add_middleware(RequestIdMiddleware)
    app.add_exception_handler(DomainError, domain_error_handler)
    app.include_router(health.router)
    app.include_router(metrics.router)
    app.include_router(v1.router)
    return app


app = create_app()
