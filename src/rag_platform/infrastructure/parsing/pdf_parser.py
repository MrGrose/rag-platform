import io

from pypdf import PdfReader

from rag_platform.application.ports.parsing import PagedDocumentParser


class PdfParser(PagedDocumentParser):
    mime_types = frozenset({"application/pdf"})

    def parse_pages(self, content: bytes) -> list[tuple[int, str]]:
        reader = PdfReader(io.BytesIO(content))
        return [
            (number, page.extract_text() or "") for number, page in enumerate(reader.pages, start=1)
        ]

    def parse(self, content: bytes) -> str:
        return "\n".join(text for _page, text in self.parse_pages(content))
