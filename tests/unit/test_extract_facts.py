import json
from datetime import UTC, datetime
from uuid import uuid4

import pytest

from rag_platform.application.extraction.schema import parse_payload
from rag_platform.application.use_cases.extract_facts import ExtractFacts
from rag_platform.domain.entities import Document, DocumentChunk
from rag_platform.domain.enums import DocumentStatus
from rag_platform.domain.errors import ValidationError
from rag_platform.infrastructure.providers.fake_llm import FakeLlmProvider


class _DocRepo:
    def __init__(self, document: Document) -> None:
        self._document = document

    async def get_by_id(self, document_id):
        return self._document if document_id == self._document.id else None


class _ChunkRepo:
    def __init__(self, chunks: list[DocumentChunk]) -> None:
        self._chunks = chunks

    async def list_for_document(self, document_id):
        return [chunk for chunk in self._chunks if chunk.document_id == document_id]


class _Llm:
    model_name = "stub"

    def __init__(self, payload: dict) -> None:
        self._payload = payload

    async def complete(self, system_prompt: str, user_prompt: str):
        from rag_platform.application.ports.llm import LlmCompletion

        return LlmCompletion(text=json.dumps(self._payload), citation_chunk_ids=[])


def _document(kb_id):
    now = datetime.now(tz=UTC)
    return Document(
        id=uuid4(),
        knowledge_base_id=kb_id,
        organization_id=uuid4(),
        filename="contract.md",
        mime_type="text/markdown",
        size_bytes=100,
        status=DocumentStatus.READY,
        storage_key="key",
        content_hash="hash",
        content_version=1,
        error_message=None,
        deleted_at=None,
        created_at=now,
        updated_at=now,
    )


def _chunk(document, index: int, content: str) -> DocumentChunk:
    now = datetime.now(tz=UTC)
    return DocumentChunk(
        id=uuid4(),
        document_id=document.id,
        knowledge_base_id=document.knowledge_base_id,
        organization_id=document.organization_id,
        chunk_index=index,
        content=content,
        embedding=[0.0] * 4,
        token_count=10,
        created_at=now,
        updated_at=now,
    )


def test_parse_payload_accepts_code_fence() -> None:
    payload = parse_payload('```json\n{"parties": [{"text": "Acme", "quote": "Acme Ltd"}]}\n```')
    assert payload.parties[0].text == "Acme"


def test_parse_payload_rejects_non_json() -> None:
    with pytest.raises(ValidationError):
        parse_payload("no json here")


async def test_extract_locates_quotes_and_reports_missing_fields() -> None:
    kb_id = uuid4()
    document = _document(kb_id)
    first = _chunk(document, 0, "Acme Ltd pays 1000 EUR within 30 days.")
    second = _chunk(document, 1, "Either party may terminate with 60 days notice.")
    llm = _Llm(
        {
            "parties": [{"text": "Acme Ltd", "quote": "Acme Ltd pays"}],
            "amounts": [{"text": "1000 EUR", "quote": "1000 EUR"}],
            "obligations": [{"text": "notice", "quote": "not in the document"}],
        }
    )
    use_case = ExtractFacts(
        doc_repo=_DocRepo(document), chunk_repo=_ChunkRepo([first, second]), llm=llm
    )
    result = await use_case.execute(knowledge_base_id=kb_id, document_id=document.id)

    assert result.payload.parties[0].text == "Acme Ltd"
    assert result.citations[0].chunk_index == 0
    assert result.citations[1].chunk_index == 0
    assert result.citations[2].chunk_id is None
    assert "risks" in result.missing
    assert "parties" not in result.missing


async def test_extract_requires_indexed_document() -> None:
    kb_id = uuid4()
    document = _document(kb_id)
    use_case = ExtractFacts(
        doc_repo=_DocRepo(document),
        chunk_repo=_ChunkRepo([]),
        llm=FakeLlmProvider(),
    )
    with pytest.raises(ValidationError):
        await use_case.execute(knowledge_base_id=kb_id, document_id=document.id)
