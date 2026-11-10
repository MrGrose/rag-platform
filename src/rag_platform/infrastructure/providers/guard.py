from rag_platform.config import Settings, get_settings
from rag_platform.domain.errors import ConfigurationError


def require_fake_providers_allowed(settings: Settings | None = None) -> None:
    cfg = settings or get_settings()
    if not cfg.allow_fake_providers:
        raise ConfigurationError(
            "ALLOW_FAKE_PROVIDERS=false requires configured production LLM/embedding providers"
        )
