import io

from pypdf import PdfReader

from rag_platform.application.ports.parsing import DocumentParser


class PdfParser(DocumentParser):
    mime_types = frozenset({"application/pdf"})

    def parse(self, content: bytes) -> str:
        reader = PdfReader(io.BytesIO(content))
        pages = [page.extract_text() or "" for page in reader.pages]
        return "\n".join(pages)
