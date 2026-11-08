import hashlib
import hmac
import secrets


def generate_api_key() -> tuple[str, str]:
    prefix = secrets.token_hex(4)
    secret = secrets.token_urlsafe(32)
    return prefix, f"rk_{prefix}_{secret}"


def hash_api_key(full_key: str, pepper: str) -> str:
    return hmac.new(pepper.encode("utf-8"), full_key.encode("utf-8"), hashlib.sha256).hexdigest()


def verify_api_key(full_key: str, pepper: str, expected_hash: str) -> bool:
    digest = hash_api_key(full_key, pepper)
    return hmac.compare_digest(digest, expected_hash)


def parse_key_prefix(full_key: str) -> str | None:
    parts = full_key.split("_", 2)
    if len(parts) != 3 or parts[0] != "rk":
        return None
    return parts[1]
