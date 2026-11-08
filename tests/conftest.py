import contextlib
import os
import subprocess
from pathlib import Path

import pytest
import pytest_asyncio
from sqlalchemy import text

from rag_platform.config.settings import get_settings
from rag_platform.infrastructure.db.session import dispose_engine, get_engine, reset_session_state

ROOT = Path(__file__).resolve().parents[1]


def pytest_configure(config: pytest.Config) -> None:
    config.addinivalue_line("markers", "integration: requires postgres/redis")


@pytest.fixture(autouse=True)
def test_security_settings(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("APP_ENV", "test")
    monkeypatch.setenv("ALLOW_OPEN_API", "true")
    monkeypatch.setenv("ALLOW_FAKE_PROVIDERS", "true")
    monkeypatch.setenv("API_KEY_HASH_PEPPER", "test-pepper-do-not-use-in-prod")
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()


@pytest.fixture(scope="session")
def integration_database_url() -> str:
    return os.environ.get(
        "DATABASE_URL",
        "postgresql+asyncpg://rag:rag@localhost:5436/rag",
    )


@pytest.fixture(scope="session", autouse=True)
def apply_alembic_migrations(integration_database_url: str) -> None:
    env = os.environ.copy()
    env["DATABASE_URL"] = integration_database_url
    with contextlib.suppress(subprocess.CalledProcessError, FileNotFoundError):
        subprocess.run(
            ["uv", "run", "alembic", "upgrade", "head"],
            cwd=ROOT,
            env=env,
            check=True,
            capture_output=True,
        )


@pytest_asyncio.fixture
async def db_engine(integration_database_url: str, monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("DATABASE_URL", integration_database_url)
    get_settings.cache_clear()
    reset_session_state()
    engine = get_engine()
    try:
        async with engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
    except Exception as exc:
        pytest.skip(f"postgres unavailable: {exc}")
    yield engine
    await dispose_engine()
    get_settings.cache_clear()


@pytest_asyncio.fixture(autouse=True)
async def isolate_integration_db_engine(request: pytest.FixtureRequest):
    if "integration" not in request.keywords:
        yield
        return
    reset_session_state()
    get_settings.cache_clear()
    yield
    await dispose_engine()
    reset_session_state()
    get_settings.cache_clear()
