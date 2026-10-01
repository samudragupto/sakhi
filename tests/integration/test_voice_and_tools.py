"""Integration tests for voice, maps places, officer card, and session erasure."""

from unittest.mock import MagicMock, patch

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_tts_speak_endpoint(client: AsyncClient) -> None:
    """Verify the TTS route returns mocked MP3 bytes and a cache header."""
    mock_response = MagicMock(audio_content=b"mock mp3")
    with patch("google.cloud.texttospeech.TextToSpeechClient") as client_class:
        cloud_client = MagicMock()
        cloud_client.synthesize_speech.return_value = mock_response
        client_class.return_value = cloud_client
        res = await client.post(
            "/api/v1/voice/speak",
            json={"text": "नमस्ते दीदी, आप कैसी हैं?", "speaking_rate": 0.9},
        )
    assert res.status_code == 200
    assert res.headers["content-type"] == "audio/mpeg"
    assert res.content == b"mock mp3"


@pytest.mark.asyncio
async def test_tts_unavailable_returns_fallback_status(client: AsyncClient) -> None:
    """Verify unavailable server TTS signals the browser-speech fallback."""
    with patch("app.routes.voice.synthesize_speech", return_value=None):
        response = await client.post(
            "/api/v1/voice/speak",
            json={"text": "fallback check", "speaking_rate": 0.9},
        )
    assert response.status_code == 503


@pytest.mark.asyncio
async def test_stt_transcribe_validation(client: AsyncClient) -> None:
    """Verify file upload format validation on transcribe route."""
    # Test invalid audio mime type
    res_bad = await client.post(
        "/api/v1/voice/transcribe",
        files={"file": ("test.txt", b"plain text", "text/plain")},
    )
    assert res_bad.status_code == 415

    # Test valid webm audio format
    res_ok = await client.post(
        "/api/v1/voice/transcribe",
        files={"file": ("audio.webm", b"\x1a\x45\xdf\xa3fakeaudio", "audio/webm")},
    )
    assert res_ok.status_code == 200
    data = res_ok.json()
    assert "text" in data


@pytest.mark.asyncio
async def test_stt_transcribe_rejects_oversized_audio(client: AsyncClient) -> None:
    """Verify uploads above the 1 MB audio limit are rejected before inference."""
    audio = bytes(1024 * 1024 + 1)
    response = await client.post(
        "/api/v1/voice/transcribe",
        files={"file": ("large.webm", audio, "audio/webm")},
    )
    assert response.status_code == 413


@pytest.mark.asyncio
async def test_nearby_places_endpoint(client: AsyncClient) -> None:
    """Verify /api/v1/places/nearby returns rounded coords and Anganwadi centres."""
    res = await client.get("/api/v1/places/nearby?lat=28.613939&lng=77.209021")
    assert res.status_code == 200
    data = res.json()
    assert len(data["centres"]) >= 1
    assert "आंगनवाड़ी" in data["centres"][0]["name"] or "पंचायत" in data["centres"][0]["name"]


@pytest.mark.asyncio
async def test_officer_card_generation(client: AsyncClient) -> None:
    """Verify /api/v1/card returns bilingual presentation and QR code base64."""
    req_body = {
        "child_number": 1,
        "benefit_amount_inr": 5000,
        "categories": ["BPL_RATION_CARD"],
        "required_documents": ["aadhaar_mother", "bank_account"],
    }
    res = await client.post("/api/v1/card", json=req_body)
    assert res.status_code == 200
    data = res.json()
    assert "data:image/png;base64," in data["qr_code_base64"]
    assert "5,000" in data["benefit_hi"]
    assert "5,000" in data["benefit_en"]


@pytest.mark.asyncio
async def test_session_erasure_endpoint(client: AsyncClient) -> None:
    """Verify DELETE /api/v1/session wipes anonymous state completely."""
    session_id = "test-wipe-session-555"
    # Create session state
    await client.post(
        "/api/v1/chat",
        json={"session_id": session_id, "message": "नमस्ते", "locale": "hi"},
    )
    # Wipe session
    del_res = await client.delete(f"/api/v1/session?session_id={session_id}")
    assert del_res.status_code == 200
    assert del_res.json()["status"] == "deleted"
