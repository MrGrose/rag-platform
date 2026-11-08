class NoopKnowledgeBaseVersion:
    async def bump(self, knowledge_base_id: str) -> None:
        _ = knowledge_base_id

    async def current(self, knowledge_base_id: str) -> str:
        _ = knowledge_base_id
        return "0"
