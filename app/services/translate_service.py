"""Cloud Translation service with timeout and deterministic dictionary fallback."""

import asyncio

from app.core.config import get_settings
from app.core.logging import logger
from app.services.eligibility import load_locale_data


def _translate_with_cloud(text: str, target_language: str, project_id: str) -> str:
    """Execute a single bounded Google Cloud Translation v3 request."""
    from google.cloud import translate

    client = translate.TranslationServiceClient()
    parent = f"projects/{project_id}/locations/global"
    response = client.translate_text(
        request={
            "parent": parent,
            "contents": [text],
            "mime_type": "text/plain",
            "source_language_code": "hi",
            "target_language_code": target_language,
        },
        timeout=5.0,
    )
    if response.translations:
        translated_text: str = response.translations[0].translated_text
        return translated_text
    return text


async def translate_text(text: str, target_language: str = "en") -> str:
    """Translate Hindi text to target language with 5.0s timeout and safe fallback."""
    if target_language == "en":
        en_locales = load_locale_data("en")
        for _key, val in en_locales.get("reasons", {}).items():
            if isinstance(val, str) and val.lower() == text.lower():
                return val

    settings = get_settings()
    if settings.environment in ("development", "test") and not settings.google_cloud_project:
        return text

    try:
        return await asyncio.to_thread(
            _translate_with_cloud, text, target_language, settings.google_cloud_project
        )
    except Exception:
        logger.warning(
            "Cloud Translation failed, using fallback text",
            extra={"event": "translation_fallback"},
        )
        return text
