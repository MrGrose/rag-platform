import rag_platform


def test_package_import() -> None:
    assert rag_platform.__version__ == "0.1.0"
