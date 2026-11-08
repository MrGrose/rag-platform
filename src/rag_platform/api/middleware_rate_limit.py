import asyncio
from collections.abc import Awaitable, Callable

import redis.asyncio as redis
import structlog
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse, Response

from rag_platform.config import get_settings

_PUBLIC_PATHS = {"/health", "/ready", "/metrics"}

_log = structlog.get_logger(__name__)


def _rate_limit_keys(request: Request) -> list[str]:
    host = request.client.host if request.client else "unknown"
    keys = [f"rl:ip:{host}"]
    settings = get_settings()
    provided_key = request.headers.get("X-API-Key", "")
    if settings.api_key and provided_key == settings.api_key:
        keys.append("rl:apikey:global")
        org = request.headers.get("X-Organization-Id", "").strip()
        if org:
            keys.append(f"rl:org:{org}")
    return keys


class RateLimitMiddleware(BaseHTTPMiddleware):
    async def dispatch(
        self,
        request: Request,
        call_next: Callable[[Request], Awaitable[Response]],
    ) -> Response:
        if request.url.path in _PUBLIC_PATHS:
            return await call_next(request)
        settings = get_settings()
        client = redis.from_url(str(settings.redis_url), decode_responses=True)
        try:
            keys = _rate_limit_keys(request)
            for key in keys:
                count = await client.incr(key)
                if count == 1:
                    await client.expire(key, 60)
                if count > settings.rate_limit_per_minute:
                    return JSONResponse(status_code=429, content={"detail": "rate limit exceeded"})
        except asyncio.CancelledError:
            raise
        except (
            ConnectionError,
            OSError,
            TimeoutError,
            redis.ConnectionError,
            redis.TimeoutError,
        ) as exc:
            _log.warning("rate_limit_redis_unavailable", error=type(exc).__name__)
            if settings.rate_limit_fail_closed:
                return JSONResponse(
                    status_code=503,
                    content={"detail": "rate limiter unavailable"},
                )
        finally:
            await client.aclose()
        return await call_next(request)
