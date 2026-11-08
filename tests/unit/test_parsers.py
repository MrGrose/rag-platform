from rag_platform.infrastructure.parsing.registry import default_parser_registry


def test_parser_registry_txt() -> None:
    text = default_parser_registry().parse("text/plain", b"Hello")
    assert text == "Hello"
