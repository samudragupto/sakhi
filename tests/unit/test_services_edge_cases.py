"""Unit tests for service fallbacks, caching, security, and logging."""

import json
import logging
from datetime import UTC, datetime, timedelta
from unittest.mock import MagicMock, patch

import pytest

from app.core.logging import RedactingJsonFormatter, setup_logging
from app.core.security import sanitize_text
from app.models.session import SessionDoc
from app.services.gemini_service import process_chat
from app.services.maps_service import find_nearby_centres
from app.services.session_service import _LOCAL_SESSIONS, delete_session, get_or_create_session
from app.services.speech_service import transcribe_audio
from app.services.tts_service import _CACHE_MAX_SIZE, _TTS_CACHE, synthesize_speech


@pytest.mark.asyncio
async def test_tts_cache_hit() -> None:
    """Test that second synthesis of identical text hits the LRU cache."""
    text = "नमस्ते दीदी, यह परीक्षण वाक्य है।"
    mock_response = MagicMock(audio_content=b"mock-audio")
    with patch("google.cloud.texttospeech.TextToSpeechClient") as client_class:
        client = MagicMock()
        client.synthesize_speech.return_value = mock_response
        client_class.return_value = client

        audio1 = await synthesize_speech(text)
        audio2 = await synthesize_speech(text)

    assert audio1 == audio2 == b"mock-audio"
    client.synthesize_speech.assert_called_once()


@pytest.mark.asyncio
async def test_tts_cache_evicts_least_recently_used_entry() -> None:
    """Verify the bounded audio cache evicts its oldest entry before insertion."""
    _TTS_CACHE.clear()
    for index in range(_CACHE_MAX_SIZE):
        _TTS_CACHE[f"cache-{index}"] = b"cached"
    with patch("app.services.tts_service._synthesize_with_cloud", return_value=b"new-audio"):
        result = await synthesize_speech("cache eviction test")
    assert result == b"new-audio"
    assert len(_TTS_CACHE) == _CACHE_MAX_SIZE
    assert "cache-0" not in _TTS_CACHE
    _TTS_CACHE.clear()


@pytest.mark.asyncio
async def test_maps_places_fallback_generation() -> None:
    """Test nearby centres return default Anganwadi locations when API key is unset."""
    resp = await find_nearby_centres(28.6139, 77.2090)
    assert len(resp.centres) == 3
    assert "आंगनवाड़ी" in resp.centres[0].name


@pytest.mark.asyncio
async def test_speech_service_wav_and_ogg() -> None:
    """Test speech service handles wav and ogg content type paths."""
    res_wav = await transcribe_audio(b"fake wav bytes", content_type="audio/wav")
    assert res_wav.text is not None

    res_ogg = await transcribe_audio(b"fake ogg bytes", content_type="audio/ogg")
    assert res_ogg.text is not None


@pytest.mark.asyncio
async def test_chat_scripted_fallback_branches() -> None:
    """Test specific conversational branches in scripted fallback."""
    with patch("app.services.gemini_service.get_gemini_client", return_value=None):
        session = SessionDoc(session_id="test-branches", step=1)

        # User says "नहीं" at step 1
        res1 = await process_chat("नहीं", session)
        assert res1.ui_action == "SHOW_RESULT"
        assert "स्तनपान" in res1.speech_text

        # User at step 2 asks for 2nd child
        session2 = SessionDoc(session_id="test-child2", step=2)
        res2 = await process_chat("दूसरी संतान", session2)
        assert res2.ui_action == "ASK_YES_NO"
        assert "बेटी" in res2.speech_text

        # User at step 3 says not a girl
        session3 = SessionDoc(session_id="test-child2-boy", step=3)
        res3 = await process_chat("नहीं, बेटा है", session3)
        assert res3.ui_action == "SHOW_RESULT"
        assert "कन्या" in res3.speech_text

        # User at step 4 selects e-shram
        session4 = SessionDoc(session_id="test-eshram", step=4)
        res4 = await process_chat("ई-श्रम", session4)
        assert res4.ui_action == "ASK_YES_NO"
        assert "सरकारी" in res4.speech_text


@pytest.mark.asyncio
async def test_chat_retries_and_positive_deterministic_branches() -> None:
    """Cover retry prompts, positive girl-child flow, and final rule outcomes."""
    with patch("app.services.gemini_service.get_gemini_client", return_value=None):
        retry = await process_chat("अस्पष्ट", SessionDoc(session_id="retry", step=2))
        assert retry.ui_action == "ASK_CHOICE"

        girl_session = SessionDoc(session_id="girl", step=3)
        category = await process_chat("हाँ, बेटी", girl_session)
        assert category.ui_action == "ASK_CHOICE"

        eligible_session = SessionDoc(session_id="eligible", step=4)
        await process_chat("मेरे पास कार्ड है", eligible_session)
        eligible = await process_chat("नहीं", eligible_session)
        assert eligible.data["eligible"] is True
        assert eligible.data["benefit_amount_inr"] == 5000

        excluded_session = SessionDoc(session_id="excluded", step=4)
        await process_chat("none", excluded_session)
        excluded = await process_chat("हाँ, सरकारी नौकरी", excluded_session)
        assert excluded.data["reason_code"] == "INELIGIBLE_GOVT_EMPLOYEE"


@pytest.mark.asyncio
async def test_expired_session_is_replaced_and_unknown_delete_is_false() -> None:
    """Cover expired local session replacement and deletion of absent state."""
    session_id = "expired-session"
    _LOCAL_SESSIONS[session_id] = SessionDoc(
        session_id=session_id,
        expire_at=datetime.now(UTC) - timedelta(seconds=1),
    )
    with patch("app.services.session_service._get_firestore_client", return_value=None):
        current = await get_or_create_session(session_id)
        deleted = await delete_session(session_id)
        absent = await delete_session("never-created")
    assert current.expire_at > datetime.now(UTC)
    assert deleted is True
    assert absent is False


def test_sanitize_text_edge_cases() -> None:
    """Test text sanitization with control characters and empty string."""
    assert sanitize_text("") == ""
    dirty = "Hello\x00\x08World\x1f!"
    assert sanitize_text(dirty) == "HelloWorld!"


def test_setup_logging_formatting() -> None:
    """Test logger configuration and JSON formatting."""
    log = setup_logging("DEBUG")
    assert log is not None


def test_log_formatter_omits_free_text_and_keeps_allowlisted_fields() -> None:
    """Ensure log output excludes arbitrary messages and retains safe telemetry."""
    record = logging.LogRecord(
        "sakhi", logging.INFO, "test.py", 1, "personal name and phone 9876543210", (), None
    )
    record.session_id = "could-contain-user-content"
    record.latency_ms = 12
    record.status_code = 200
    record.event = "request_complete"

    output = json.loads(RedactingJsonFormatter().format(record))

    assert "session_id" not in output
    assert output["latency_ms"] == 12
    assert output["status_code"] == 200
    assert output["event"] == "request_complete"
    assert "message" not in output
    assert "9876543210" not in json.dumps(output)

    without_event = logging.LogRecord("sakhi", logging.INFO, "test.py", 1, "safe", (), None)
    assert "event" not in json.loads(RedactingJsonFormatter().format(without_event))
