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
        pages = self.parse_pages(mime_type, content)
        return "\n".join(text for _page, text in pages)

    def parse_pages(self, mime_type: str, content: bytes) -> list[tuple[int, str]]:
        parser = self._by_mime.get(mime_type)
        if parser is None:
            raise ValidationError(f"unsupported mime type: {mime_type}")
        try:
            parse_pages = getattr(parser, "parse_pages", None)
            if parse_pages is not None:
                return parse_pages(content)
            return [(1, parser.parse(content))]
        except Exception as exc:
            raise ValidationError(f"failed to parse document: {exc}") from exc


def default_parser_registry() -> ParserRegistry:
    return ParserRegistry([PlainTextParser(), MarkdownParser(), PdfParser()])
