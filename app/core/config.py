"""Application configuration module using pydantic-settings.

Loads environment variables with fallbacks and supports optional Google Secret Manager.
Never hardcodes secrets or credentials.
"""

from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Configuration settings for Sakhi application."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    app_name: str = Field(default="Sakhi – आपकी आवाज़ दीदी", alias="APP_NAME")
    app_env: str = Field(default="development", alias="APP_ENV")
    debug: bool = Field(default=False, alias="DEBUG")
    log_level: str = Field(default="INFO", alias="LOG_LEVEL")

    # Google Cloud
    gcp_project_id: str = Field(default="", alias="GCP_PROJECT_ID")
    use_secret_manager: bool = Field(default=False, alias="USE_SECRET_MANAGER")

    # Gemini API
    gemini_model: str = Field(default="gemini-2.5-flash", alias="GEMINI_MODEL")
    gemini_api_key: str = Field(default="", alias="GEMINI_API_KEY")

    # Google Maps Places API
    google_maps_api_key: str = Field(default="", alias="GOOGLE_MAPS_API_KEY")

    # Firestore
    firestore_database: str = Field(default="(default)", alias="FIRESTORE_DATABASE")
    firestore_session_ttl_hours: int = Field(default=24, alias="FIRESTORE_SESSION_TTL_HOURS")

    # Security & CORS
    allowed_origins: list[str] = Field(
        default=["http://localhost:8080", "http://127.0.0.1:8080"],
        alias="ALLOWED_ORIGINS",
    )
    trusted_hosts: list[str] = Field(
        default=["localhost", "127.0.0.1", "0.0.0.0", "testserver"],
        alias="TRUSTED_HOSTS",
    )
    rate_limit_default: str = Field(default="100/minute", alias="RATE_LIMIT_DEFAULT")
    rate_limit_chat: str = Field(default="20/minute", alias="RATE_LIMIT_CHAT")
    rate_limit_voice: str = Field(default="20/minute", alias="RATE_LIMIT_VOICE")
    rate_limit_vision: str = Field(default="5/minute", alias="RATE_LIMIT_VISION")


def load_secret_from_gcp(secret_id: str, project_id: str) -> str | None:
    """Fetch secret payload safely from Google Secret Manager.

    Returns None if unreachable or credentials are unavailable.
    """
    try:
        from google.cloud import secretmanager

        client = secretmanager.SecretManagerServiceClient()
        name = f"projects/{project_id}/secrets/{secret_id}/versions/latest"
        response = client.access_secret_version(request={"name": name}, timeout=5.0)
        return response.payload.data.decode("UTF-8")
    except Exception:
        return None


@lru_cache
def get_settings() -> Settings:
    """Return cached singleton instance of application settings."""
    settings = Settings()
    if settings.use_secret_manager and settings.gcp_project_id:
        # Attempt to load keys if configured
        gemini_secret = load_secret_from_gcp("GEMINI_API_KEY", settings.gcp_project_id)
        if gemini_secret:
            settings.gemini_api_key = gemini_secret
        maps_secret = load_secret_from_gcp("GOOGLE_MAPS_API_KEY", settings.gcp_project_id)
        if maps_secret:
            settings.google_maps_api_key = maps_secret
    return settings
