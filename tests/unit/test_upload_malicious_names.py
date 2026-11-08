import pytest

from rag_platform.application.validation.upload import validate_upload
from rag_platform.domain.errors import ValidationError


def test_rejects_path_traversal_filename() -> None:
    with pytest.raises(ValidationError):
        validate_upload("../../../etc/passwd", "text/plain", 12)


def test_rejects_null_byte_in_filename() -> None:
    with pytest.raises(ValidationError):
        validate_upload("evil\x00.txt", "text/plain", 12)
