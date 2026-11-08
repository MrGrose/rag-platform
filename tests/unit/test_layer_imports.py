import importlib


def test_layer_imports() -> None:
    for mod in (
        "rag_platform.domain",
        "rag_platform.application",
        "rag_platform.application.ports",
        "rag_platform.infrastructure",
        "rag_platform.api",
        "rag_platform.workers",
    ):
        importlib.import_module(mod)
