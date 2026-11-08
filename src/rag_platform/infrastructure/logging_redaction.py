import re

_SECRET_PATTERNS = (
    re.compile(r"(?i)((?:api[_-]?key|password|secret|token)\s*[:=])\s*\S+"),
    re.compile(r"Bearer\s+\S+"),
)


def redact_message(message: str) -> str:
    redacted = message
    for pattern in _SECRET_PATTERNS:
        if "Bearer" in pattern.pattern:
            redacted = pattern.sub("Bearer ***", redacted)
        else:
            redacted = pattern.sub(r"\1***", redacted)
    if len(redacted) > 4000:
        return redacted[:4000] + "…[truncated]"
    return redacted


def redact_log_processor(_logger, _method_name: str, event_dict: dict) -> dict:
    for key in ("event", "msg", "message"):
        if key in event_dict and isinstance(event_dict[key], str):
            event_dict[key] = redact_message(event_dict[key])
    if "body" in event_dict and isinstance(event_dict["body"], str):
        event_dict["body"] = "[redacted]"
    return event_dict
