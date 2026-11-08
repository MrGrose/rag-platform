import pytest

from rag_platform.application.validation.upload import sanitize_filename, validate_upload
from rag_platform.domain.errors import ValidationError


def test_sanitize_filename_rejects_path_traversal() -> None:
    with pytest.raises(ValidationError):
        sanitize_filename("../../notes.txt")


def test_validate_upload_rejects_large_file() -> None:
    with pytest.raises(ValidationError):
        validate_upload("a.pdf", "application/pdf", 30 * 1024 * 1024)


def test_validate_upload_accepts_pdf() -> None:
    name = validate_upload("doc.pdf", "application/pdf", 1024)
    assert name == "doc.pdf"
