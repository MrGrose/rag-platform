from uuid import UUID, uuid4

import pytest
from httpx import ASGITransport, AsyncClient

from rag_platform.api.app import create_app
from rag_platform.api.deps import get_db_session, get_object_storage
from rag_platform.infrastructure.db.session import session_scope
from rag_platform.infrastructure.fakes.storage import InMemoryObjectStorage

DEFAULT_ORG_ID = UUID("00000000-0000-4000-8000-000000000001")
DEFAULT_KB_ID = UUID("00000000-0000-4000-8000-000000000002")
_ORG_HEADERS = {"X-Organization-Id": str(DEFAULT_ORG_ID)}


@pytest.mark.integration
@pytest.mark.asyncio
async def test_documents_list_get_delete_roundtrip() -> None:
    storage = InMemoryObjectStorage()

    async def override_session():
        async with session_scope() as session:
            yield session

    app = create_app()
    app.dependency_overrides[get_db_session] = override_session
    app.dependency_overrides[get_object_storage] = lambda: storage
    suffix = uuid4().hex
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        payload = f"api integration {suffix}".encode()
        files = {"file": (f"api-{suffix}.txt", payload, "text/plain")}
        data = {"knowledge_base_id": str(DEFAULT_KB_ID)}
        created = await client.post(
            "/v1/documents",
            data=data,
            files=files,
            headers=_ORG_HEADERS,
        )
        assert created.status_code == 202, created.text
        doc_id = created.json()["id"]
        listed = await client.get(
            "/v1/documents",
            params={"knowledge_base_id": str(DEFAULT_KB_ID)},
            headers=_ORG_HEADERS,
        )
        assert listed.status_code == 200
        assert any(item["id"] == doc_id for item in listed.json()["items"])
        detail = await client.get(
            f"/v1/documents/{doc_id}",
            params={"knowledge_base_id": str(DEFAULT_KB_ID)},
            headers=_ORG_HEADERS,
        )
        assert detail.status_code == 200
        deleted = await client.delete(
            f"/v1/documents/{doc_id}",
            params={"knowledge_base_id": str(DEFAULT_KB_ID)},
            headers=_ORG_HEADERS,
        )
        assert deleted.status_code == 204
        missing = await client.get(
            f"/v1/documents/{doc_id}",
            params={"knowledge_base_id": str(DEFAULT_KB_ID)},
            headers=_ORG_HEADERS,
        )
        assert missing.status_code == 404
