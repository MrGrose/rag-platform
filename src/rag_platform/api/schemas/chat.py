from uuid import UUID

from pydantic import BaseModel, Field

from rag_platform.domain.entities import ChatResult


class ChatRequest(BaseModel):
    knowledge_base_id: UUID
    question: str = Field(min_length=1, max_length=4000)


class CitationResponse(BaseModel):
    chunk_id: UUID
    document_id: UUID
    snippet: str


class ChatResponse(BaseModel):
    query_id: UUID
    answer: str
    citations: list[CitationResponse]
    insufficient_context: bool

    @classmethod
    def from_result(cls, result: ChatResult) -> "ChatResponse":
        return cls(
            query_id=result.query_id,
            answer=result.answer,
            insufficient_context=result.insufficient_context,
            citations=[
                CitationResponse(
                    chunk_id=c.chunk_id,
                    document_id=c.document_id,
                    snippet=c.snippet,
                )
                for c in result.citations
            ],
        )
