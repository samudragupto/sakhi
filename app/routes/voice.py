"""Endpoints for voice transcription (STT) and audio synthesis (TTS)."""

from fastapi import APIRouter, File, HTTPException, Request, Response, UploadFile

from app.core.config import get_settings
from app.core.rate_limit import limiter
from app.core.security import sanitize_text
from app.models.voice import SpeakRequest, TranscribeResponse
from app.services.speech_service import transcribe_audio
from app.services.tts_service import synthesize_speech

router = APIRouter(prefix="/api/v1/voice", tags=["Voice"])

MAX_AUDIO_SIZE_BYTES = 1 * 1024 * 1024  # 1 MB
ALLOWED_AUDIO_TYPES = {"audio/webm", "audio/ogg", "audio/wav", "audio/x-wav"}


@router.post("/transcribe", response_model=TranscribeResponse)
@limiter.limit(get_settings().rate_limit_voice)
async def transcribe_voice(
    request: Request,
    file: UploadFile = File(...),
) -> TranscribeResponse:
    """Transcribe spoken Hindi audio using Cloud Speech-to-Text with validation."""
    content_type = file.content_type or ""
    if not any(t in content_type.lower() for t in ["webm", "ogg", "wav", "octet-stream"]):
        raise HTTPException(status_code=415, detail="Unsupported audio format")

    content = await file.read()
    if len(content) > MAX_AUDIO_SIZE_BYTES:
        raise HTTPException(status_code=413, detail="Audio file exceeds 1 MB limit")

    return await transcribe_audio(content, content_type)


@router.post("/speak")
@limiter.limit(get_settings().rate_limit_voice)
async def speak_text(
    request: Request,
    body: SpeakRequest,
) -> Response:
    """Convert Hindi text to MP3 audio stream with LRU caching."""
    clean_text = sanitize_text(body.text, max_length=1000)
    audio_bytes = await synthesize_speech(clean_text, speaking_rate=body.speaking_rate)
    if audio_bytes is None:
        return Response(status_code=503)
    return Response(
        content=audio_bytes,
        media_type="audio/mpeg",
        headers={"Cache-Control": "public, max-age=86400"},
    )
