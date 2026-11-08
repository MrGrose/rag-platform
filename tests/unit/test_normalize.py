import pytest

from rag_platform.application.processing.normalize import assert_text_within_limit, normalize_text


def test_normalize_collapses_whitespace() -> None:
    assert normalize_text("hello   world\n\n\t!") == "hello world !"


def test_assert_text_within_limit_raises() -> None:
    with pytest.raises(ValueError):
        assert_text_within_limit("x" * 100, 10)
