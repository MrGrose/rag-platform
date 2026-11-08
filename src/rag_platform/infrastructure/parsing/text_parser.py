from rag_platform.application.ports.parsing import DocumentParser


class PlainTextParser(DocumentParser):
    mime_types = frozenset({"text/plain"})

    def parse(self, content: bytes) -> str:
        return content.decode("utf-8", errors="replace")


class MarkdownParser(DocumentParser):
    mime_types = frozenset({"text/markdown", "text/x-markdown"})

    def parse(self, content: bytes) -> str:
        return content.decode("utf-8", errors="replace")
