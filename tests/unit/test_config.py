"""Unit tests for configuration and environment loading."""

from unittest.mock import patch

from app.core.config import Settings, get_settings


def test_default_settings() -> None:
    """Test default values of configuration."""
    settings = Settings()
    assert "Sakhi" in settings.app_name
    assert settings.debug is False
    assert settings.gcp_project_id == ""
    assert settings.gemini_model == "gemini-2.5-flash"
    assert settings.firestore_session_ttl_hours == 24


def test_get_settings_cached() -> None:
    """Test that get_settings provides a singleton instance."""
    s1 = get_settings()
    s2 = get_settings()
    assert s1 is s2


def test_get_settings_loads_configured_secrets() -> None:
    """Verify both configured Secret Manager values override environment defaults."""
    get_settings.cache_clear()
    settings = Settings(use_secret_manager=True, gcp_project_id="test")
    try:
        with patch("app.core.config.Settings", return_value=settings):
            with patch(
                "app.core.config.load_secret_from_gcp",
                side_effect=["test-gemini", "test-maps"],
            ) as secret_loader:
                loaded = get_settings()
            assert loaded.gemini_api_key == "test-gemini"
            assert loaded.google_maps_api_key == "test-maps"
        assert secret_loader.call_count == 2
    finally:
        get_settings.cache_clear()


def test_get_settings_skips_secret_manager_without_configuration() -> None:
    """Verify Secret Manager is skipped when disabled or missing a project ID."""
    for settings in (
        Settings(use_secret_manager=False, gcp_project_id="test"),
        Settings(use_secret_manager=True, gcp_project_id=""),
    ):
        get_settings.cache_clear()
        with patch("app.core.config.Settings", return_value=settings):
            with patch("app.core.config.load_secret_from_gcp") as secret_loader:
                assert get_settings() is settings
                secret_loader.assert_not_called()
    get_settings.cache_clear()


def test_get_settings_ignores_unavailable_secret_values() -> None:
    """Verify missing Secret Manager values preserve empty environment defaults."""
    get_settings.cache_clear()
    settings = Settings(use_secret_manager=True, gcp_project_id="test")
    try:
        with patch("app.core.config.Settings", return_value=settings):
            with patch("app.core.config.load_secret_from_gcp", return_value=None):
                loaded = get_settings()
        assert loaded.gemini_api_key == ""
        assert loaded.google_maps_api_key == ""
    finally:
        get_settings.cache_clear()
