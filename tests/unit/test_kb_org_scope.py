from uuid import UUID, uuid4

import pytest

from rag_platform.api.deps_auth import verify_kb_tenant_scope
from rag_platform.domain.errors import NotFoundError, ValidationError
from rag_platform.domain.tenant import TenantContext


class _FakeKbRepo:
    def __init__(self, kb) -> None:
        self._kb = kb

    async def get_by_id(self, _kid):
        return self._kb


class _FakeKb:
    def __init__(self, org_id: UUID) -> None:
        self.organization_id = org_id


def _tenant(org: UUID) -> TenantContext:
    return TenantContext(
        organization_id=org,
        api_key_id=uuid4(),
        scopes=("*",),
        auth_mode="api_key",
    )


@pytest.mark.asyncio
async def test_missing_kb_raises_not_found(monkeypatch: pytest.MonkeyPatch) -> None:
    import rag_platform.api.deps_auth as mod

    monkeypatch.setattr(
        mod,
        "SqlAlchemyKnowledgeBaseRepository",
        lambda _s: _FakeKbRepo(None),
    )
    kid = uuid4()
    org = uuid4()
    with pytest.raises(NotFoundError):
        await verify_kb_tenant_scope(kid, session=None, tenant=_tenant(org))


@pytest.mark.asyncio
async def test_org_mismatch_raises(monkeypatch: pytest.MonkeyPatch) -> None:
    import rag_platform.api.deps_auth as mod

    org_kb = uuid4()
    monkeypatch.setattr(
        mod,
        "SqlAlchemyKnowledgeBaseRepository",
        lambda _s: _FakeKbRepo(_FakeKb(org_kb)),
    )
    kid = uuid4()
    with pytest.raises(ValidationError):
        await verify_kb_tenant_scope(kid, session=None, tenant=_tenant(uuid4()))


@pytest.mark.asyncio
async def test_matching_org_returns_id(monkeypatch: pytest.MonkeyPatch) -> None:
    import rag_platform.api.deps_auth as mod

    org = uuid4()
    monkeypatch.setattr(
        mod,
        "SqlAlchemyKnowledgeBaseRepository",
        lambda _s: _FakeKbRepo(_FakeKb(org)),
    )
    kid = uuid4()
    got = await verify_kb_tenant_scope(kid, session=None, tenant=_tenant(org))
    assert got == org
