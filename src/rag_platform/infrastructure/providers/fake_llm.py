import re

from rag_platform.application.ports.llm import LlmCompletion, LlmProvider

_CHUNK_ID = re.compile(
    r"[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}",
    re.IGNORECASE,
)


class FakeLlmProvider(LlmProvider):
    model_name = "fake-llm-v1"

    async def complete(self, system_prompt: str, user_prompt: str) -> LlmCompletion:
        _ = system_prompt
        chunk_ids = _CHUNK_ID.findall(user_prompt)
        citation_ids = chunk_ids[:3]
        if citation_ids:
            answer = f"Answer grounded on {len(citation_ids)} source(s)."
        else:
            answer = "I do not have enough information in the knowledge base."
        return LlmCompletion(text=answer, citation_chunk_ids=citation_ids)
