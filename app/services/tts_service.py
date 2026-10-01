"""Text-to-Speech service using Google Cloud TTS Neural2 voice with LRU caching.

Features an in-memory hash cache for zero-cost repeated synthesis of prompts.
"""

import asyncio
import hashlib
from collections import OrderedDict

from app.core.logging import logger

# In-memory LRU cache storing synthesized audio MP3 bytes (max 128 prompts)
_TTS_CACHE: OrderedDict[str, bytes] = OrderedDict()
_CACHE_MAX_SIZE = 128


def _synthesize_with_cloud(text: str, speaking_rate: float, voice_name: str) -> bytes:
    """Perform one Google Text-to-Speech request with a five-second deadline."""
    from google.cloud import texttospeech

    client = texttospeech.TextToSpeechClient()
    speech_input = texttospeech.SynthesisInput(text=text)
    voice = texttospeech.VoiceSelectionParams(language_code="hi-IN", name=voice_name)
    audio_config = texttospeech.AudioConfig(
        audio_encoding=texttospeech.AudioEncoding.MP3,
        speaking_rate=speaking_rate,
    )
    response = client.synthesize_speech(
        input=speech_input,
        voice=voice,
        audio_config=audio_config,
        timeout=5.0,
    )
    return response.audio_content


def _get_cache_key(text: str, voice_name: str, rate: float) -> str:
    """Generate SHA-256 hash for cache key."""
    raw = f"{text}_{voice_name}_{rate}"
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


async def synthesize_speech(
    text: str,
    speaking_rate: float = 0.9,
    voice_name: str = "hi-IN-Neural2-A",
) -> bytes | None:
    """Synthesize Hindi speech via Cloud TTS with LRU caching and fallback."""
    cache_key = _get_cache_key(text, voice_name, speaking_rate)

    # Check cache hit
    if cache_key in _TTS_CACHE:
        _TTS_CACHE.move_to_end(cache_key)
        return _TTS_CACHE[cache_key]

    try:
        audio_bytes = await asyncio.to_thread(
            _synthesize_with_cloud, text, speaking_rate, voice_name
        )
        if len(_TTS_CACHE) >= _CACHE_MAX_SIZE:
            _TTS_CACHE.popitem(last=False)
        _TTS_CACHE[cache_key] = audio_bytes
        return audio_bytes
    except Exception:
        logger.warning(
            "Cloud TTS unavailable, browser speech will be used",
            extra={"event": "tts_fallback"},
        )
        return None
