from rag_platform.application.ports.embeddings import EmbeddingProvider
from rag_platform.application.ports.llm import LlmProvider
from rag_platform.application.ports.reranker import RerankerProvider
from rag_platform.config import Settings, get_settings
from rag_platform.domain.errors import ConfigurationError
from rag_platform.infrastructure.providers.bge_m3_embeddings import BgeM3EmbeddingProvider
from rag_platform.infrastructure.providers.bge_reranker import BgeRerankerProvider
from rag_platform.infrastructure.providers.fake_embeddings import FakeEmbeddingProvider
from rag_platform.infrastructure.providers.fake_llm import FakeLlmProvider
from rag_platform.infrastructure.providers.fake_reranker import FakeRerankerProvider
from rag_platform.infrastructure.providers.guard import require_fake_providers_allowed
from rag_platform.infrastructure.providers.openai_llm import OpenAiCompatibleLlmProvider

_BGE_NAMES = {"bge", "bge_m3", "bge-m3", "bge_reranker", "bge-reranker"}


def build_embeddings(settings: Settings | None = None) -> EmbeddingProvider:
    cfg = settings or get_settings()
    name = cfg.embeddings_provider.strip().lower()
    if name == "fake":
        require_fake_providers_allowed(cfg)
        return FakeEmbeddingProvider()
    if name in _BGE_NAMES:
        return BgeM3EmbeddingProvider(
            model_name=cfg.embeddings_model,
            device=cfg.embeddings_device,
            batch_size=cfg.embeddings_batch_size,
        )
    raise ConfigurationError(f"unknown embeddings provider: {cfg.embeddings_provider}")


def build_reranker(settings: Settings | None = None) -> RerankerProvider:
    cfg = settings or get_settings()
    name = cfg.reranker_provider.strip().lower()
    if name == "fake":
        require_fake_providers_allowed(cfg)
        return FakeRerankerProvider()
    if name in _BGE_NAMES:
        return BgeRerankerProvider(
            model_name=cfg.reranker_model,
            device=cfg.embeddings_device,
            batch_size=cfg.embeddings_batch_size,
        )
    raise ConfigurationError(f"unknown reranker provider: {cfg.reranker_provider}")


def build_llm(settings: Settings | None = None) -> LlmProvider:
    cfg = settings or get_settings()
    name = cfg.llm_provider.strip().lower()
    if name == "fake":
        require_fake_providers_allowed(cfg)
        return FakeLlmProvider()
    if name in {"openai", "openai-compatible", "deepseek"}:
        return OpenAiCompatibleLlmProvider(
            base_url=cfg.llm_base_url,
            api_key=cfg.llm_api_key,
            model=cfg.llm_model,
            timeout_seconds=cfg.llm_timeout_seconds,
            max_retries=cfg.llm_max_retries,
            temperature=cfg.llm_temperature,
            max_tokens=cfg.chat_max_output_tokens,
        )
    raise ConfigurationError(f"unknown llm provider: {cfg.llm_provider}")
