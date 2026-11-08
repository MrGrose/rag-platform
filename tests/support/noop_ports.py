class NoopKnowledgeBaseVersion:
    async def bump(self, knowledge_base_id: str) -> None:
        return None

    async def current(self, knowledge_base_id: str) -> str:
        return "0"
