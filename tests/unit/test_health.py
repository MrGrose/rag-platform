from unittest.mock import AsyncMock, patch

from fastapi.testclient import TestClient

from rag_platform.api.app import create_app


def test_health_liveness() -> None:
    client = TestClient(create_app())
    assert client.get("/health").json() == {"status": "ok"}


def test_health_ready_when_dependencies_ok() -> None:
    client = TestClient(create_app())
    with (
        patch(
            "rag_platform.api.routers.health.check_postgres",
            new_callable=AsyncMock,
            return_value=True,
        ),
        patch(
            "rag_platform.api.routers.health.check_redis",
            new_callable=AsyncMock,
            return_value=True,
        ),
    ):
        assert client.get("/ready").json() == {"status": "ready"}


def test_health_ready_returns_503_when_postgres_down() -> None:
    client = TestClient(create_app())
    with patch(
        "rag_platform.api.routers.health.check_postgres",
        new_callable=AsyncMock,
        side_effect=RuntimeError("db down"),
    ):
        response = client.get("/ready")
    assert response.status_code == 503
