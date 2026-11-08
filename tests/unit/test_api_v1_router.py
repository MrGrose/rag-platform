from fastapi.testclient import TestClient

from rag_platform.api.app import create_app
from rag_platform.api.constants import API_PREFIX
from rag_platform.api.routers import v1


def test_v1_router_mounted() -> None:
    assert v1.router.prefix == API_PREFIX
    app = create_app()
    client = TestClient(app)
    assert client.get("/health").status_code == 200
