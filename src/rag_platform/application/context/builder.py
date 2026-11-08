from rag_platform.domain.entities import RetrievalHit


def estimate_tokens(text: str) -> int:
    return max(1, len(text.split()))


def build_context(hits: list[RetrievalHit], token_budget: int) -> tuple[str, list[RetrievalHit]]:
    selected: list[RetrievalHit] = []
    used = 0
    seen: set = set()
    for hit in hits:
        if hit.chunk_id in seen:
            continue
        chunk_tokens = estimate_tokens(hit.content)
        if used + chunk_tokens > token_budget:
            break
        seen.add(hit.chunk_id)
        selected.append(hit)
        used += chunk_tokens
    blocks = [f"[{hit.chunk_id}] {hit.content}" for hit in selected]
    return "\n\n".join(blocks), selected
