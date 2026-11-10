import pytest

from rag_platform.config.settings import Settings
from rag_platform.domain.errors import ConfigurationError, ServiceUnavailableError
from rag_platform.infrastructure.providers.bge_m3_embeddings import BgeM3EmbeddingProvider
from rag_platform.infrastructure.providers.bge_reranker import BgeRerankerProvider
from rag_platform.infrastructure.providers.factory import (
    build_embeddings,
    build_llm,
    build_reranker,
)
from rag_platform.infrastructure.providers.fake_embeddings import FakeEmbeddingProvider
from rag_platform.infrastructure.providers.fake_llm import FakeLlmProvider
from rag_platform.infrastructure.providers.noop_reranker import NoopRerankerProvider
from rag_platform.infrastructure.providers.openai_llm import OpenAiCompatibleLlmProvider


def _settings(**overrides) -> Settings:
    values = {
        "APP_ENV": "test",
        "EMBEDDINGS_PROVIDER": "fake",
        "RERANKER_PROVIDER": "fake",
        "LLM_PROVIDER": "fake",
        **overrides,
    }
    return Settings(**values)


def test_defaults_select_fake_providers() -> None:
    settings = _settings()
    assert isinstance(build_embeddings(settings), FakeEmbeddingProvider)
    assert isinstance(build_llm(settings), FakeLlmProvider)


def test_fake_providers_rejected_when_disabled() -> None:
    settings = _settings(ALLOW_FAKE_PROVIDERS=False)
    with pytest.raises(ConfigurationError):
        build_embeddings(settings)
    with pytest.raises(ConfigurationError):
        build_llm(settings)


def test_bge_providers_are_selected() -> None:
    settings = _settings(EMBEDDINGS_PROVIDER="bge_m3", RERANKER_PROVIDER="bge_reranker")
    embeddings = build_embeddings(settings)
    reranker = build_reranker(settings)
    assert isinstance(embeddings, BgeM3EmbeddingProvider)
    assert embeddings.dimension == 1024
    assert isinstance(reranker, BgeRerankerProvider)


def test_openai_llm_requires_api_key() -> None:
    settings = _settings(LLM_PROVIDER="openai", LLM_API_KEY="")
    with pytest.raises(ServiceUnavailableError):
        build_llm(settings)


def test_openai_llm_uses_configured_model() -> None:
    settings = _settings(
        LLM_PROVIDER="openai",
        LLM_API_KEY="test-key",
        LLM_MODEL="deepseek-chat",
    )
    provider = build_llm(settings)
    assert isinstance(provider, OpenAiCompatibleLlmProvider)
    assert provider.model_name == "deepseek-chat"


def test_unknown_provider_is_rejected() -> None:
    settings = _settings(EMBEDDINGS_PROVIDER="unknown")
    with pytest.raises(ConfigurationError):
        build_embeddings(settings)


def test_reranker_off_keeps_retrieval_order() -> None:
    settings = _settings(RERANKER_PROVIDER="off")
    assert isinstance(build_reranker(settings), NoopRerankerProvider)
