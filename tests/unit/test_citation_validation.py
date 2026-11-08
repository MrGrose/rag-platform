import pytest

from rag_platform.application.validation.citations import validate_citations
from rag_platform.domain.errors import ValidationError


def test_validate_citations_rejects_unknown() -> None:
    with pytest.raises(ValidationError):
        validate_citations(["a"], {"b"})
