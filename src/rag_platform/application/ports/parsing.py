from typing import Protocol


class DocumentParser(Protocol):
    mime_types: frozenset[str]

    def parse(self, content: bytes) -> str: ...


class MimeParserRegistry(Protocol):
    def parse(self, mime_type: str, content: bytes) -> str: ...
