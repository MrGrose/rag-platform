from collections.abc import AsyncIterator
from uuid import uuid4

import pytest
from httpx import ASGITransport, AsyncClient

from rag_platform.api.app import create_app
from rag_platform.application.use_cases.get_evaluation import GetEvaluation
from rag_platform.application.use_cases.start_evaluation import StartEvaluation
from rag_platform.config.settings import get_settings
from rag_platform.domain.entities import EvaluationRecord, KnowledgeBase
from rag_platform.domain.errors import NotFoundError
from rag_platform.infrastructure.fakes.evaluation_repository import InMemoryEvaluationRepository
from rag_platform.infrastructure.fakes.outbox_repository import InMemoryOutboxRepository

ORG_A = uuid4()
ORG_B = uuid4()
KB_A = uuid4()
KB_B = uuid4()
EVAL_A = uuid4()


class _KbRepo:
    async def get_by_id(self, kid):
        if kid == KB_A:
            return KnowledgeBase(
                id=KB_A,
                organization_id=ORG_A,
                name="kb",
                created_at=__import__("datetime").datetime.now(__import__("datetime").UTC),
                updated_at=__import__("datetime").datetime.now(__import__("datetime").UTC),
            )
        return None


def _install_start_evaluation(monkeypatch: pytest.MonkeyPatch) -> None:
    import rag_platform.api.routers.v1.evaluations as eval_mod

    def _build_start(_session):
        return StartEvaluation(
            kb_repo=_KbRepo(),
            eval_repo=InMemoryEvaluationRepository(),
            outbox_repo=InMemoryOutboxRepository(),
        )

    async def _session_dep() -> AsyncIterator[object]:
        yield object()

    monkeypatch.setattr(eval_mod, "build_start_evaluation", _build_start)
    monkeypatch.setattr("rag_platform.api.deps.get_db_session", _session_dep)

    import rag_platform.api.deps_auth as auth_mod

    class _Kb:
        organization_id = ORG_A

    async def _get_by_id(self, _kid):
        return _Kb()

    monkeypatch.setattr(
        auth_mod,
        "SqlAlchemyKnowledgeBaseRepository",
        lambda _s: type("_Repo", (), {"get_by_id": _get_by_id})(),
    )


@pytest.mark.asyncio
async def test_post_evaluation_returns_evaluation_id(monkeypatch: pytest.MonkeyPatch) -> None:
    _install_start_evaluation(monkeypatch)
    monkeypatch.setenv("ALLOW_OPEN_API", "true")
    get_settings.cache_clear()
    app = create_app()
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        res = await client.post(
            "/v1/evaluations",
            json={"knowledge_base_id": str(KB_A)},
            headers={"X-Organization-Id": str(ORG_A)},
        )
    assert res.status_code == 202
    body = res.json()
    assert body["status"] == "pending"
    assert body["id"]
    get_settings.cache_clear()


@pytest.mark.asyncio
async def test_post_evaluation_org_mismatch_returns_422(monkeypatch: pytest.MonkeyPatch) -> None:
    import rag_platform.api.deps_auth as auth_mod

    class _Kb:
        organization_id = ORG_A

    async def _get_by_id(self, _kid):
        return _Kb()

    monkeypatch.setattr(
        auth_mod,
        "SqlAlchemyKnowledgeBaseRepository",
        lambda _s: type("_Repo", (), {"get_by_id": _get_by_id})(),
    )
    monkeypatch.setenv("ALLOW_OPEN_API", "true")
    get_settings.cache_clear()
    _install_start_evaluation(monkeypatch)
    app = create_app()
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        res = await client.post(
            "/v1/evaluations",
            json={"knowledge_base_id": str(KB_A)},
            headers={"X-Organization-Id": str(ORG_B)},
        )
    assert res.status_code == 422
    get_settings.cache_clear()


@pytest.mark.asyncio
async def test_api_key_required_when_open_api_disabled(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("ALLOW_OPEN_API", "false")
    monkeypatch.setenv("API_KEY_HASH_PEPPER", "test-pepper")
    monkeypatch.delenv("API_KEY", raising=False)
    get_settings.cache_clear()
    app = create_app()
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        res = await client.post(
            "/v1/evaluations",
            json={"knowledge_base_id": str(KB_A)},
            headers={"X-Organization-Id": str(ORG_A)},
        )
    assert res.status_code == 401
    get_settings.cache_clear()


@pytest.mark.asyncio
async def test_get_evaluation_scoped_repo_cross_kb() -> None:
    repo = InMemoryEvaluationRepository()
    await repo.seed(EVAL_A, KB_A, ORG_A, status="completed", metrics_json="{}")
    use_case = GetEvaluation(eval_repo=repo)
    with pytest.raises(NotFoundError):
        await use_case.execute(evaluation_id=EVAL_A, knowledge_base_id=KB_B, organization_id=ORG_B)


@pytest.mark.asyncio
async def test_get_evaluation_scoped_repo_success() -> None:
    repo = InMemoryEvaluationRepository()
    await repo.seed(EVAL_A, KB_A, ORG_A, status="completed", metrics_json='{"ok":1}')
    use_case = GetEvaluation(eval_repo=repo)
    row = await use_case.execute(
        evaluation_id=EVAL_A, knowledge_base_id=KB_A, organization_id=ORG_A
    )
    assert isinstance(row, EvaluationRecord)
    assert row.status == "completed"
