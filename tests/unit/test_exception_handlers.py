import pytest
from starlette.requests import Request

from rag_platform.api.exceptions import domain_error_handler
from rag_platform.domain.errors import ConflictError, NotFoundError, ValidationError


@pytest.mark.parametrize(
    ("exc", "status"),
    [
        (NotFoundError("missing"), 404),
        (ConflictError("dup"), 409),
        (ValidationError("bad"), 422),
    ],
)
async def test_domain_error_handler_maps_status(exc: Exception, status: int) -> None:
    scope = {"type": "http", "method": "GET", "path": "/", "headers": []}
    request = Request(scope)
    response = await domain_error_handler(request, exc)
    assert response.status_code == status
