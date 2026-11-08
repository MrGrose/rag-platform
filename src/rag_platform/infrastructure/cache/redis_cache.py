import hashlib
import json

import redis.asyncio as redis
import structlog

from rag_platform.config import get_settings

_logger = structlog.get_logger(__name__)


async def _client() -> redis.Redis:
    return redis.from_url(str(get_settings().redis_url), decode_responses=True)


def kb_version_key(knowledge_base_id: str) -> str:
    return f"kbversion:{knowledge_base_id}"


async def bump_kb_version(knowledge_base_id: str) -> None:
    try:
        client = await _client()
        try:
            await client.incr(kb_version_key(knowledge_base_id))
        finally:
            await client.aclose()
    except Exception as exc:
        _logger.debug("redis_cache_degraded", op="bump_kb_version", error=str(exc))


async def get_kb_version(knowledge_base_id: str) -> str:
    try:
        client = await _client()
        try:
            value = await client.get(kb_version_key(knowledge_base_id))
            return value or "0"
        finally:
            await client.aclose()
    except Exception as exc:
        _logger.debug("redis_cache_degraded", op="get_kb_version", error=str(exc))
        return "0"


async def cache_get(namespace: str, key: str) -> str | None:
    try:
        client = await _client()
        try:
            return await client.get(f"{namespace}:{key}")
        finally:
            await client.aclose()
    except Exception as exc:
        _logger.debug("redis_cache_degraded", op="cache_get", error=str(exc))
        return None


async def cache_set(namespace: str, key: str, value: str, ttl_seconds: int = 300) -> None:
    try:
        client = await _client()
        try:
            await client.setex(f"{namespace}:{key}", ttl_seconds, value)
        finally:
            await client.aclose()
    except Exception as exc:
        _logger.debug("redis_cache_degraded", op="cache_set", error=str(exc))


def hash_embedding_inputs(texts: list[str]) -> str:
    joined = "\n".join(texts)
    return hashlib.sha256(joined.encode("utf-8")).hexdigest()


def serialize_vectors(vectors: list[list[float]]) -> str:
    return json.dumps(vectors)


def deserialize_vectors(payload: str) -> list[list[float]]:
    return json.loads(payload)
