"""Application configuration module using pydantic-settings.

Loads environment variables with fallbacks. In production, secrets are mounted
as environment variables by Cloud Run from Google Secret Manager.
Never hardcodes secrets or credentials.
"""

from functools import lru_cache

from pydantic import AliasChoices, Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Configuration settings for Sakhi application."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    app_name: str = Field(
        default="Sakhi – आपकी आवाज़ दीदी",
        validation_alias=AliasChoices("APP_NAME", "app_name"),
    )
    environment: str = Field(
        default="development",
        validation_alias=AliasChoices("ENVIRONMENT", "APP_ENV", "environment", "app_env"),
    )
    debug: bool = Field(default=False, validation_alias=AliasChoices("DEBUG", "debug"))
    log_level: str = Field(default="INFO", validation_alias=AliasChoices("LOG_LEVEL", "log_level"))

    # Google Cloud
    google_cloud_project: str = Field(
        default="",
        validation_alias=AliasChoices(
            "GOOGLE_CLOUD_PROJECT",
            "GCP_PROJECT_ID",
            "google_cloud_project",
            "gcp_project_id",
        ),
    )
    google_cloud_location: str = Field(
        default="us-central1",
        validation_alias=AliasChoices("GOOGLE_CLOUD_LOCATION", "google_cloud_location"),
    )

    # Gemini via Vertex AI (ADC, no API key)
    gemini_model: str = Field(
        default="gemini-2.5-flash",
        validation_alias=AliasChoices("GEMINI_MODEL", "gemini_model"),
    )

    # Google Maps Places API (key mounted from Secret Manager as env var)
    maps_api_key: str = Field(
        default="",
        validation_alias=AliasChoices(
            "MAPS_API_KEY", "GOOGLE_MAPS_API_KEY", "maps_api_key", "google_maps_api_key"
        ),
    )

    # Firestore
    firestore_collection: str = Field(
        default="sessions",
        validation_alias=AliasChoices("FIRESTORE_COLLECTION", "firestore_collection"),
    )
    firestore_database: str = Field(
        default="(default)",
        validation_alias=AliasChoices("FIRESTORE_DATABASE", "firestore_database"),
    )
    firestore_session_ttl_hours: int = Field(
        default=24,
        validation_alias=AliasChoices("FIRESTORE_SESSION_TTL_HOURS", "firestore_session_ttl_hours"),
    )

    # Security & CORS
    allowed_origins: list[str] = Field(
        default=["http://localhost:8080", "http://127.0.0.1:8080"],
        validation_alias=AliasChoices("ALLOWED_ORIGINS", "allowed_origins"),
    )
    allowed_hosts: list[str] = Field(
        default=["localhost", "127.0.0.1", "0.0.0.0", "testserver"],
        validation_alias=AliasChoices(
            "ALLOWED_HOSTS", "TRUSTED_HOSTS", "allowed_hosts", "trusted_hosts"
        ),
    )

    rate_limit_default: str = Field(
        default="100/minute",
        validation_alias=AliasChoices("RATE_LIMIT_DEFAULT", "rate_limit_default"),
    )
    rate_limit_chat: str = Field(
        default="20/minute",
        validation_alias=AliasChoices("RATE_LIMIT_CHAT", "rate_limit_chat"),
    )
    rate_limit_voice: str = Field(
        default="20/minute",
        validation_alias=AliasChoices("RATE_LIMIT_VOICE", "rate_limit_voice"),
    )
    rate_limit_vision: str = Field(
        default="5/minute",
        validation_alias=AliasChoices("RATE_LIMIT_VISION", "rate_limit_vision"),
    )

    @property
    def gcp_project_id(self) -> str:
        """Return Google Cloud project ID from modern or legacy field."""
        return self.google_cloud_project

    @property
    def app_env(self) -> str:
        """Return environment name for backward compatibility."""
        return self.environment

    @property
    def google_maps_api_key(self) -> str:
        """Alias for maps_api_key."""
        return self.maps_api_key

    @property
    def trusted_hosts(self) -> list[str]:
        """Alias for allowed_hosts."""
        return self.allowed_hosts


@lru_cache
def get_settings() -> Settings:
    """Return cached singleton instance of application settings."""
    return Settings()
