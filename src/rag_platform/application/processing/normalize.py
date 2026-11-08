import re

_WS = re.compile(r"\s+")


def normalize_text(text: str) -> str:
    collapsed = _WS.sub(" ", text.replace("\r\n", "\n").replace("\r", "\n"))
    return collapsed.strip()


def assert_text_within_limit(text: str, max_bytes: int) -> None:
    if len(text.encode("utf-8")) > max_bytes:
        msg = f"extracted text exceeds limit ({max_bytes} bytes)"
        raise ValueError(msg)
