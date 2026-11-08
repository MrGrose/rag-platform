from fastapi import Request
from fastapi.responses import JSONResponse

from rag_platform.domain.errors import (
    ConfigurationError,
    ConflictError,
    DomainError,
    NotFoundError,
    ServiceUnavailableError,
    ValidationError,
)


async def domain_error_handler(_request: Request, exc: DomainError) -> JSONResponse:
    status = 400
    if isinstance(exc, NotFoundError):
        status = 404
    elif isinstance(exc, ConflictError):
        status = 409
    elif isinstance(exc, ValidationError):
        status = 422
    elif isinstance(exc, ServiceUnavailableError):
        status = 503
    elif isinstance(exc, ConfigurationError):
        status = 500
    return JSONResponse(status_code=status, content={"detail": str(exc)})
