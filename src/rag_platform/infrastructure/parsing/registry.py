from rag_platform.application.ports.parsing import DocumentParser
from rag_platform.domain.errors import ValidationError
from rag_platform.infrastructure.parsing.pdf_parser import PdfParser
from rag_platform.infrastructure.parsing.text_parser import MarkdownParser, PlainTextParser


class ParserRegistry:
    def __init__(self, parsers: list[DocumentParser]) -> None:
        self._by_mime: dict[str, DocumentParser] = {}
        for parser in parsers:
            for mime in parser.mime_types:
                self._by_mime[mime] = parser

    def parse(self, mime_type: str, content: bytes) -> str:
        parser = self._by_mime.get(mime_type)
        if parser is None:
            raise ValidationError(f"unsupported mime type: {mime_type}")
        try:
            return parser.parse(content)
        except Exception as exc:
            raise ValidationError(f"failed to parse document: {exc}") from exc


def default_parser_registry() -> ParserRegistry:
    return ParserRegistry([PlainTextParser(), MarkdownParser(), PdfParser()])
