from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from starlette.requests import Request

from rag_platform.api.middleware_rate_limit import RateLimitMiddleware
from rag_platform.config.settings import get_settings


@pytest.mark.asyncio
async def test_rate_limit_fail_closed_returns_503(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("RATE_LIMIT_FAIL_CLOSED", "true")
    monkeypatch.setenv("ALLOW_OPEN_API", "true")
    get_settings.cache_clear()
    middleware = RateLimitMiddleware(app=MagicMock())
    request = Request(
        {
            "type": "http",
            "method": "GET",
            "path": "/v1/chat",
            "headers": [],
            "client": ("127.0.0.1", 1234),
        }
    )

    async def call_next(_req):
        return MagicMock(status_code=200)

    mock_client = AsyncMock()
    mock_client.incr = AsyncMock(side_effect=ConnectionError("redis down"))
    mock_client.aclose = AsyncMock()
    with patch(
        "rag_platform.api.middleware_rate_limit.redis.from_url",
        return_value=mock_client,
    ):
        response = await middleware.dispatch(request, call_next)
    assert response.status_code == 503
    get_settings.cache_clear()


@pytest.mark.asyncio
async def test_rate_limit_fail_open_allows_request(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("RATE_LIMIT_FAIL_CLOSED", "false")
    monkeypatch.setenv("ALLOW_OPEN_API", "true")
    get_settings.cache_clear()
    middleware = RateLimitMiddleware(app=MagicMock())
    request = Request(
        {
            "type": "http",
            "method": "GET",
            "path": "/v1/chat",
            "headers": [],
            "client": ("127.0.0.1", 1234),
        }
    )

    async def call_next(_req):
        return MagicMock(status_code=200)

    mock_client = AsyncMock()
    mock_client.incr = AsyncMock(return_value=1)
    mock_client.expire = AsyncMock()
    mock_client.aclose = AsyncMock()

    with patch(
        "rag_platform.api.middleware_rate_limit.redis.from_url",
        return_value=mock_client,
    ):
        response = await middleware.dispatch(request, call_next)
    assert response.status_code == 200
    get_settings.cache_clear()
