"""Unit tests for configuration and environment loading."""

from app.core.config import Settings, get_settings


def test_default_settings() -> None:
    """Test default values of configuration."""
    settings = Settings()
    assert "Sakhi" in settings.app_name
    assert settings.debug is False
    assert settings.gcp_project_id == ""
    assert settings.gemini_model == "gemini-2.5-flash"
    assert settings.firestore_session_ttl_hours == 24
    assert settings.google_cloud_location == "us-central1"
    assert settings.firestore_collection == "sessions"


def test_get_settings_cached() -> None:
    """Test that get_settings provides a singleton instance."""
    s1 = get_settings()
    s2 = get_settings()
    assert s1 is s2


def test_settings_aliases_resolve() -> None:
    """Verify backward-compatible property aliases."""
    settings = Settings()
    assert settings.app_env == settings.environment
    assert settings.gcp_project_id == settings.google_cloud_project
    assert settings.google_maps_api_key == settings.maps_api_key
    assert settings.trusted_hosts == settings.allowed_hosts


def test_settings_all_optional() -> None:
    """Verify settings can be created with no environment variables at all."""
    get_settings.cache_clear()
    try:
        settings = Settings()
        assert settings.environment == "development"
        assert settings.maps_api_key == ""
        assert settings.google_cloud_project == ""
    finally:
        get_settings.cache_clear()
