import redis.asyncio as redis
from sqlalchemy import text

from rag_platform.config import get_settings
from rag_platform.infrastructure.db.session import get_engine


async def check_postgres() -> bool:
    engine = get_engine()
    async with engine.connect() as conn:
        await conn.execute(text("SELECT 1"))
    return True


async def check_redis() -> bool:
    client = redis.from_url(str(get_settings().redis_url), decode_responses=True)
    try:
        pong = await client.ping()
        return bool(pong)
    finally:
        await client.aclose()
