from dataclasses import dataclass, field
from uuid import UUID

from rag_platform.application.extraction.schema import (
    FIELDS,
    SYSTEM_PROMPT,
    ExtractionPayload,
    build_user_prompt,
    parse_payload,
)
from rag_platform.application.ports.chunks import ChunkRepository
from rag_platform.application.ports.documents import DocumentRepository
from rag_platform.application.ports.llm import LlmProvider
from rag_platform.domain.entities import DocumentChunk
from rag_platform.domain.errors import NotFoundError, ValidationError

MAX_EXTRACTION_CHARS = 24_000


@dataclass(frozen=True, slots=True)
class FactCitation:
    field: str
    chunk_id: UUID | None
    chunk_index: int | None
    quote: str
    page: int | None = None


@dataclass(frozen=True, slots=True)
class ExtractionResult:
    document_id: UUID
    payload: ExtractionPayload
    citations: list[FactCitation] = field(default_factory=list)
    missing: list[str] = field(default_factory=list)
    truncated: bool = False


def _normalize(value: str) -> str:
    return " ".join(value.split()).lower()


def _locate(quote: str, chunks: list[DocumentChunk]) -> tuple[UUID | None, int | None, int | None]:
    needle = _normalize(quote)
    if not needle:
        return None, None, None
    for chunk in chunks:
        if needle in _normalize(chunk.content):
            return chunk.id, chunk.chunk_index, chunk.page
    return None, None, None


class ExtractFacts:
    def __init__(
        self,
        *,
        doc_repo: DocumentRepository,
        chunk_repo: ChunkRepository,
        llm: LlmProvider,
    ) -> None:
        self._doc_repo = doc_repo
        self._chunk_repo = chunk_repo
        self._llm = llm

    async def execute(self, *, knowledge_base_id: UUID, document_id: UUID) -> ExtractionResult:
        document = await self._doc_repo.get_by_id(document_id)
        if document is None or document.knowledge_base_id != knowledge_base_id:
            raise NotFoundError(f"document not found: {document_id}")
        chunks = await self._chunk_repo.list_for_document(document_id)
        if not chunks:
            raise ValidationError("document is not indexed yet")
        text = "\n\n".join(f"[chunk {chunk.chunk_index}] {chunk.content}" for chunk in chunks)
        truncated = len(text) > MAX_EXTRACTION_CHARS
        text = text[:MAX_EXTRACTION_CHARS]
        completion = await self._llm.complete(SYSTEM_PROMPT, build_user_prompt(text))
        payload = parse_payload(completion.text)

        citations: list[FactCitation] = []
        for name in FIELDS:
            for fact in getattr(payload, name):
                chunk_id, chunk_index, page = _locate(fact.quote, chunks)
                citations.append(
                    FactCitation(
                        field=name,
                        chunk_id=chunk_id,
                        chunk_index=chunk_index,
                        quote=fact.quote,
                        page=page,
                    )
                )
        missing = sorted(
            set(payload.missing) | {name for name in FIELDS if not getattr(payload, name)}
        )
        return ExtractionResult(
            document_id=document_id,
            payload=payload,
            citations=citations,
            missing=missing,
            truncated=truncated,
        )
