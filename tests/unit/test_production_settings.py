import pytest
from pydantic import ValidationError

from rag_platform.config.settings import Settings


def test_production_rejects_open_api() -> None:
    with pytest.raises(ValidationError):
        Settings(
            APP_ENV="production",
            API_KEY_HASH_PEPPER="pepper",
            ALLOW_OPEN_API=True,
            RATE_LIMIT_FAIL_CLOSED=True,
            ALLOW_FAKE_PROVIDERS=False,
        )


def test_production_requires_api_key_pepper() -> None:
    with pytest.raises(ValidationError):
        Settings(
            APP_ENV="production",
            API_KEY_HASH_PEPPER="",
            ALLOW_OPEN_API=False,
            RATE_LIMIT_FAIL_CLOSED=True,
            ALLOW_FAKE_PROVIDERS=False,
        )


def test_production_requires_fail_closed_rate_limit() -> None:
    with pytest.raises(ValidationError):
        Settings(
            APP_ENV="production",
            API_KEY_HASH_PEPPER="pepper",
            ALLOW_OPEN_API=False,
            RATE_LIMIT_FAIL_CLOSED=False,
            ALLOW_FAKE_PROVIDERS=False,
        )


def test_production_rejects_legacy_global_api_key() -> None:
    with pytest.raises(ValidationError):
        Settings(
            APP_ENV="production",
            API_KEY_HASH_PEPPER="pepper",
            ALLOW_OPEN_API=False,
            RATE_LIMIT_FAIL_CLOSED=True,
            ALLOW_FAKE_PROVIDERS=False,
            ALLOW_LEGACY_GLOBAL_API_KEY=True,
        )


def test_development_allows_explicit_open_api() -> None:
    s = Settings(
        APP_ENV="development",
        ALLOW_OPEN_API=True,
        API_KEY="",
    )
    assert s.allow_open_api is True
