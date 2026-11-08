import hashlib
import json
from uuid import UUID

from rag_platform.application.ports.retrieval import RetrievalEngine
from rag_platform.domain.entities import RetrievalHit
from rag_platform.infrastructure.cache.redis_cache import cache_get, cache_set, get_kb_version


def _serialize_hits(hits: list[RetrievalHit]) -> str:
    payload = [
        {
            "chunk_id": str(h.chunk_id),
            "document_id": str(h.document_id),
            "knowledge_base_id": str(h.knowledge_base_id),
            "content": h.content,
            "score": h.score,
            "rank": h.rank,
        }
        for h in hits
    ]
    return json.dumps(payload)


def _deserialize_hits(payload: str) -> list[RetrievalHit]:
    rows = json.loads(payload)
    return [
        RetrievalHit(
            chunk_id=UUID(row["chunk_id"]),
            document_id=UUID(row["document_id"]),
            knowledge_base_id=UUID(row["knowledge_base_id"]),
            content=row["content"],
            score=float(row["score"]),
            rank=int(row["rank"]),
        )
        for row in rows
    ]


class CachedRetrievalEngine(RetrievalEngine):
    def __init__(self, inner: RetrievalEngine) -> None:
        self._inner = inner

    async def retrieve(
        self,
        *,
        organization_id: UUID,
        knowledge_base_id: UUID,
        question: str,
        limit: int,
    ) -> list[RetrievalHit]:
        version = await get_kb_version(str(knowledge_base_id))
        digest = hashlib.sha256(question.encode("utf-8")).hexdigest()
        cache_key = f"{organization_id}:{version}:{digest}:{limit}"
        cached = await cache_get("retr", cache_key)
        if cached is not None:
            return _deserialize_hits(cached)
        hits = await self._inner.retrieve(
            organization_id=organization_id,
            knowledge_base_id=knowledge_base_id,
            question=question,
            limit=limit,
        )
        await cache_set("retr", cache_key, _serialize_hits(hits), ttl_seconds=300)
        return hits
