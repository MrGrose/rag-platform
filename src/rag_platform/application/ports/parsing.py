from typing import Protocol


class DocumentParser(Protocol):
    mime_types: frozenset[str]

    def parse(self, content: bytes) -> str: ...


class PagedDocumentParser(DocumentParser, Protocol):
    def parse_pages(self, content: bytes) -> list[tuple[int, str]]: ...


class MimeParserRegistry(Protocol):
    def parse(self, mime_type: str, content: bytes) -> str: ...

    def parse_pages(self, mime_type: str, content: bytes) -> list[tuple[int, str]]: ...
