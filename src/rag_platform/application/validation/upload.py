import os.path
import re

from rag_platform.domain.errors import ValidationError

MAX_UPLOAD_BYTES = 25 * 1024 * 1024
ALLOWED_MIME_TYPES = frozenset(
    {
        "application/pdf",
        "text/plain",
        "text/markdown",
    },
)

_SAFE_NAME = re.compile(r"[^a-zA-Z0-9._-]+")


def sanitize_filename(filename: str) -> str:
    if "\x00" in filename:
        raise ValidationError("invalid filename")
    normalized = filename.replace("\\", "/").strip()
    segments = [part for part in normalized.split("/") if part]
    if any(part == ".." for part in segments):
        raise ValidationError("invalid filename")
    base = os.path.basename(normalized)
    if not base or base in {".", ".."}:
        raise ValidationError("invalid filename")
    cleaned = _SAFE_NAME.sub("_", base)
    if not cleaned:
        raise ValidationError("invalid filename")
    return cleaned[:255]


def validate_upload(filename: str, mime_type: str, size_bytes: int) -> str:
    safe_name = sanitize_filename(filename)
    if size_bytes <= 0 or size_bytes > MAX_UPLOAD_BYTES:
        raise ValidationError("file size not allowed")
    if mime_type not in ALLOWED_MIME_TYPES:
        raise ValidationError("mime type not allowed")
    return safe_name
