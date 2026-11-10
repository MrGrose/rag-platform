import asyncio

import httpx
import pytest

from rag_platform.domain.errors import ServiceUnavailableError
from rag_platform.infrastructure.providers.openai_llm import OpenAiCompatibleLlmProvider

CHUNK = "11111111-1111-1111-1111-111111111111"


def _provider(
    transport: httpx.AsyncBaseTransport, *, retries: int = 2
) -> OpenAiCompatibleLlmProvider:
    return OpenAiCompatibleLlmProvider(
        base_url="https://llm.test/v1",
        api_key="test-key",
        model="test-model",
        timeout_seconds=5,
        max_retries=retries,
    )


def _patch_client(monkeypatch, transport: httpx.AsyncBaseTransport) -> None:
    original = httpx.AsyncClient

    def factory(*args, **kwargs):
        kwargs["transport"] = transport
        return original(*args, **kwargs)

    monkeypatch.setattr(httpx, "AsyncClient", factory)
    monkeypatch.setattr(asyncio, "sleep", _no_sleep)


async def _no_sleep(_seconds: float) -> None:
    return None


async def test_completion_returns_text_and_citations(monkeypatch) -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path.endswith("/chat/completions")
        return httpx.Response(
            200,
            json={"choices": [{"message": {"content": f"Answer [{CHUNK}]"}}]},
        )

    _patch_client(monkeypatch, httpx.MockTransport(handler))
    completion = await _provider(httpx.MockTransport(handler)).complete("system", "user")
    assert completion.text == f"Answer [{CHUNK}]"
    assert completion.citation_chunk_ids == [CHUNK]


async def test_rate_limit_is_retried(monkeypatch) -> None:
    calls = {"count": 0}

    def handler(request: httpx.Request) -> httpx.Response:
        calls["count"] += 1
        if calls["count"] == 1:
            return httpx.Response(429, json={"error": "slow down"})
        return httpx.Response(200, json={"choices": [{"message": {"content": "ok"}}]})

    transport = httpx.MockTransport(handler)
    _patch_client(monkeypatch, transport)
    completion = await _provider(transport).complete("system", "user")
    assert completion.text == "ok"
    assert calls["count"] == 2


async def test_client_error_is_not_retried(monkeypatch) -> None:
    calls = {"count": 0}

    def handler(request: httpx.Request) -> httpx.Response:
        calls["count"] += 1
        return httpx.Response(401, json={"error": "bad key"})

    transport = httpx.MockTransport(handler)
    _patch_client(monkeypatch, transport)
    with pytest.raises(ServiceUnavailableError):
        await _provider(transport).complete("system", "user")
    assert calls["count"] == 1


async def test_exhausted_retries_raise(monkeypatch) -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(503, json={"error": "unavailable"})

    transport = httpx.MockTransport(handler)
    _patch_client(monkeypatch, transport)
    with pytest.raises(ServiceUnavailableError):
        await _provider(transport, retries=1).complete("system", "user")
