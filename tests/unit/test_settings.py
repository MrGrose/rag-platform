from rag_platform.config.settings import Settings


def test_settings_defaults() -> None:
    s = Settings()
    assert s.app_env
    assert "5436" in str(s.database_url)
