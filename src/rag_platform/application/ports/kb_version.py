from typing import Protocol


class KnowledgeBaseVersionPort(Protocol):
    async def bump(self, knowledge_base_id: str) -> None: ...

    async def current(self, knowledge_base_id: str) -> str: ...
