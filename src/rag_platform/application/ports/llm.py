from dataclasses import dataclass
from typing import Protocol


@dataclass(frozen=True, slots=True)
class LlmCompletion:
    text: str
    citation_chunk_ids: list[str]


class LlmProvider(Protocol):
    model_name: str

    async def complete(self, system_prompt: str, user_prompt: str) -> LlmCompletion: ...
