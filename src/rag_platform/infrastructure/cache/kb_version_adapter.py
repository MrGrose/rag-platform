from rag_platform.application.ports.kb_version import KnowledgeBaseVersionPort
from rag_platform.infrastructure.cache.redis_cache import bump_kb_version, get_kb_version


class RedisKnowledgeBaseVersionPort(KnowledgeBaseVersionPort):
    async def bump(self, knowledge_base_id: str) -> None:
        await bump_kb_version(knowledge_base_id)

    async def current(self, knowledge_base_id: str) -> str:
        return await get_kb_version(knowledge_base_id)
