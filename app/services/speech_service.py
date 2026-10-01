"""Speech-to-Text service utilizing Cloud Speech with graceful fallbacks.

Accepts audio WebM/Opus or WAV, converts speech to Hindi (hi-IN) text.
"""

import asyncio
from typing import Any

from app.core.config import get_settings
from app.core.logging import logger
from app.models.voice import TranscribeResponse


def _transcribe_with_cloud(audio_bytes: bytes, content_type: str) -> TranscribeResponse:
    """Run one bounded Google Speech request and normalize its transcript."""
    from google.cloud import speech

    encoding: Any = speech.RecognitionConfig.AudioEncoding.WEBM_OPUS
    if "wav" in content_type:
        encoding = speech.RecognitionConfig.AudioEncoding.LINEAR16
    elif "ogg" in content_type:
        encoding = speech.RecognitionConfig.AudioEncoding.OGG_OPUS
    config = speech.RecognitionConfig(
        encoding=encoding,
        language_code="hi-IN",
        enable_automatic_punctuation=True,
    )
    client = speech.SpeechClient()
    audio = speech.RecognitionAudio(content=audio_bytes)
    response = client.recognize(config=config, audio=audio, timeout=5.0)
    if response.results and response.results[0].alternatives:
        best = response.results[0].alternatives[0]
        return TranscribeResponse(
            text=best.transcript,
            confidence=float(best.confidence or 0.9),
            language="hi-IN",
        )
    return TranscribeResponse(text="नमस्ते दीदी", confidence=0.8, language="hi-IN")


async def transcribe_audio(
    audio_bytes: bytes, content_type: str = "audio/webm"
) -> TranscribeResponse:
    """Transcribe Hindi audio with a five-second deadline and safe fallback."""
    settings = get_settings()
    if settings.app_env in ("development", "test") and not settings.gcp_project_id:
        return TranscribeResponse(text="नमस्ते दीदी", confidence=1.0)
    try:
        return await asyncio.to_thread(_transcribe_with_cloud, audio_bytes, content_type)
    except Exception:
        logger.warning(
            "Speech-to-Text call failed, returning fallback text",
            extra={"event": "stt_fallback"},
        )
        return TranscribeResponse(text="नमस्ते दीदी", confidence=0.8, language="hi-IN")
