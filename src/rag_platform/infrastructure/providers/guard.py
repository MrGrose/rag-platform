from rag_platform.config import get_settings
from rag_platform.domain.errors import ConfigurationError


def require_fake_providers_allowed() -> None:
    if not get_settings().allow_fake_providers:
        raise ConfigurationError(
            "ALLOW_FAKE_PROVIDERS=false requires configured production LLM/embedding providers"
        )
