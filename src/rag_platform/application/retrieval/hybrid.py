from uuid import UUID

from rag_platform.domain.entities import RetrievalHit


def _normalize_scores(items: list[tuple[UUID, UUID, UUID, str, float]]) -> dict[UUID, float]:
    if not items:
        return {}
    scores = [score for *_, score in items]
    min_s = min(scores)
    max_s = max(scores)
    if max_s <= min_s:
        return {chunk_id: 1.0 for chunk_id, *_ in items}
    return {chunk_id: (score - min_s) / (max_s - min_s) for chunk_id, *_, score in items}


def fuse_hits(
    vector: list[tuple[UUID, UUID, UUID, str, float]],
    lexical: list[tuple[UUID, UUID, UUID, str, float]],
    limit: int,
) -> list[RetrievalHit]:
    v_norm = _normalize_scores(vector)
    l_norm = _normalize_scores(lexical)
    merged: dict[UUID, tuple[UUID, UUID, str, float]] = {}
    for chunk_id, doc_id, kb_id, content, _ in vector:
        merged[chunk_id] = (doc_id, kb_id, content, 0.5 * v_norm.get(chunk_id, 0.0))
    for chunk_id, doc_id, kb_id, content, _ in lexical:
        base = merged.get(chunk_id)
        lexical_score = 0.5 * l_norm.get(chunk_id, 0.0)
        if base is None:
            merged[chunk_id] = (doc_id, kb_id, content, lexical_score)
        else:
            doc_id, kb_id, content, combined = base
            merged[chunk_id] = (doc_id, kb_id, content, combined + lexical_score)
    ranked = sorted(merged.items(), key=lambda item: item[1][3], reverse=True)[:limit]
    hits: list[RetrievalHit] = []
    for index, (chunk_id, (doc_id, kb_id, content, score)) in enumerate(ranked, start=1):
        hits.append(
            RetrievalHit(
                chunk_id=chunk_id,
                document_id=doc_id,
                knowledge_base_id=kb_id,
                content=content,
                score=score,
                rank=index,
            ),
        )
    return hits
