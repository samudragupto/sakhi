"""Unit tests for Firestore mock, Places mock, and Gemini mock to hit >= 90% coverage."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.core.config import load_secret_from_gcp
from app.services.gemini_service import explain_document_image
from app.services.maps_service import find_nearby_centres
from app.services.session_service import (
    _LOCAL_SESSIONS,
    _get_firestore_client,
    delete_session,
    get_or_create_session,
    update_session,
)
from app.services.speech_service import transcribe_audio
from app.services.tts_service import synthesize_speech


@pytest.mark.asyncio
async def test_session_service_firestore_branches() -> None:
    """Mock firestore client to test firestore persistence paths."""
    mock_db = MagicMock()
    mock_doc_ref = MagicMock()
    mock_doc = MagicMock()
    mock_doc.exists = True
    mock_doc.to_dict.return_value = {
        "session_id": "mock-fs-123",
        "step": 2,
        "answers": {},
        "created_at": "2026-10-01T00:00:00Z",
        "expire_at": "2026-10-02T00:00:00Z",
    }
    mock_doc_ref.get.return_value = mock_doc
    mock_db.collection.return_value.document.return_value = mock_doc_ref

    with patch("app.services.session_service._get_firestore_client", return_value=mock_db):
        sess = await get_or_create_session("mock-fs-123")
        assert sess.step == 2
        mock_doc_ref.get.assert_called_once_with(timeout=5.0)

        await update_session(sess)
        mock_doc_ref.set.assert_called_once_with(sess.model_dump(), timeout=5.0)

        deleted = await delete_session("mock-fs-123")
        assert deleted is True
        mock_doc_ref.delete.assert_called_once_with(timeout=5.0)


@pytest.mark.asyncio
async def test_firestore_missing_document_and_timeout_fallbacks() -> None:
    """Cover Firestore creation and local fallbacks for each failed operation."""
    db = MagicMock()
    missing_ref = MagicMock()
    missing_ref.get.return_value.exists = False
    db.collection.return_value.document.return_value = missing_ref
    with patch("app.services.session_service._get_firestore_client", return_value=db):
        created = await get_or_create_session("mock-firestore-miss")
    assert created.step == 1
    missing_ref.set.assert_called_once_with(created.model_dump(), timeout=5.0)

    failing_db = MagicMock()
    failing_ref = MagicMock()
    failing_ref.get.side_effect = TimeoutError
    failing_ref.set.side_effect = TimeoutError
    failing_ref.delete.side_effect = TimeoutError
    failing_db.collection.return_value.document.return_value = failing_ref
    with patch("app.services.session_service._get_firestore_client", return_value=failing_db):
        local_session = await get_or_create_session("mock-firestore-timeout")
        await update_session(local_session)
        assert await delete_session(local_session.session_id) is True
    assert failing_ref.get.call_args.kwargs["timeout"] == 5.0
    assert failing_ref.set.call_args.kwargs["timeout"] == 5.0
    assert failing_ref.delete.call_args.kwargs["timeout"] == 5.0


@pytest.mark.asyncio
async def test_local_session_fallback_is_bounded() -> None:
    """Verify expired and oldest local sessions are evicted at the store limit."""
    original_sessions = _LOCAL_SESSIONS.copy()
    _LOCAL_SESSIONS.clear()
    try:
        with patch("app.services.session_service._LOCAL_SESSION_MAX_SIZE", 1):
            with patch("app.services.session_service._get_firestore_client", return_value=None):
                await get_or_create_session("first-local-session")
                await get_or_create_session("second-local-session")
        assert len(_LOCAL_SESSIONS) == 1
        assert "second-local-session" in _LOCAL_SESSIONS
    finally:
        _LOCAL_SESSIONS.clear()
        _LOCAL_SESSIONS.update(original_sessions)


def test_firestore_client_configuration_and_failure() -> None:
    """Verify production Firestore initialization is mocked and degrades safely."""
    settings = MagicMock(app_env="production", gcp_project_id="test", firestore_database="default")
    with patch("app.services.session_service.get_settings", return_value=settings):
        with patch("google.cloud.firestore.Client") as client_class:
            client_class.return_value = MagicMock()
            assert _get_firestore_client() is client_class.return_value
            client_class.side_effect = RuntimeError
            assert _get_firestore_client() is None


@pytest.mark.asyncio
async def test_places_service_http_mock() -> None:
    """Test Places API with configured API key and successful mock response."""
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {
        "places": [
            {
                "displayName": {"text": "परीक्षण आंगनवाड़ी केंद्र"},
                "formattedAddress": "मुख्य ग्राम पंचायत",
                "location": {"latitude": 28.62, "longitude": 77.21},
            }
        ]
    }

    mock_client = MagicMock()
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=None)
    mock_client.post = AsyncMock(return_value=mock_response)

    with patch("app.services.maps_service.get_settings") as mock_settings:
        mock_settings.return_value.google_maps_api_key = "test"
        with patch("httpx.AsyncClient", return_value=mock_client) as client_class:
            resp = await find_nearby_centres(28.61, 77.20)
            assert len(resp.centres) >= 1
            assert "परीक्षण" in resp.centres[0].name
            assert resp.centres[0].distance_km > 0
            assert "query=28.62,77.21" in resp.centres[0].maps_url
        client_class.assert_called_once_with(timeout=4.0)
        mock_client.post.assert_awaited_once()


@pytest.mark.asyncio
async def test_places_http_error_and_timeout_fall_back() -> None:
    """Verify Places non-success and timeout responses return generic centres."""
    response = MagicMock(status_code=503)
    missing_location = MagicMock(
        status_code=200,
        json=MagicMock(return_value={"places": [{"displayName": {"text": "No coordinates"}}]}),
    )
    mock_client = MagicMock()
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=None)
    mock_client.post = AsyncMock(side_effect=[response, missing_location, TimeoutError()])
    with patch("app.services.maps_service.get_settings") as settings:
        settings.return_value.google_maps_api_key = "test"
        with patch("httpx.AsyncClient", return_value=mock_client):
            first = await find_nearby_centres(28.61, 77.20)
            second = await find_nearby_centres(28.61, 77.20)
            third = await find_nearby_centres(28.61, 77.20)
    assert len(first.centres) == len(second.centres) == len(third.centres) == 3
    assert mock_client.post.await_count == 3


@pytest.mark.asyncio
async def test_gemini_document_summary_mock() -> None:
    """Test Gemini document summary uses mocked response and bounded timeout."""
    mock_response = MagicMock()
    mock_response.text = "इस पत्र में आवेदन की तारीख दी गई है।"

    with patch("app.services.gemini_service.get_settings") as mock_settings:
        mock_settings.return_value.gemini_api_key = "test"
        mock_settings.return_value.gemini_model = "gemini-2.5-flash"

        with patch("google.genai.Client") as mock_client_cls:
            mock_client = MagicMock()
            mock_client.models.generate_content.return_value = mock_response
            mock_client_cls.return_value = mock_client

            resp = await explain_document_image(b"mock-image", "image/jpeg")
            assert "आवेदन" in resp.summary_hi
            assert mock_client_cls.call_args.kwargs["http_options"].timeout == 5000
            assert (
                mock_client.models.generate_content.call_args.kwargs["model"] == "gemini-2.5-flash"
            )


@pytest.mark.asyncio
async def test_gemini_missing_key_and_timeout_use_local_guidance() -> None:
    """Verify Gemini is skipped without credentials and falls back on failures."""
    with patch("app.services.gemini_service.get_settings") as settings:
        settings.return_value.gemini_api_key = ""
        without_key = await explain_document_image(b"image", "image/jpeg")
        assert "फोटो" in without_key.summary_hi

        settings.return_value.gemini_api_key = "test"
        settings.return_value.gemini_model = "gemini-2.5-flash"
        with patch("google.genai.Client") as client_class:
            client_class.return_value.models.generate_content.side_effect = TimeoutError
            timed_out = await explain_document_image(b"image", "image/jpeg")
    assert timed_out == without_key


@pytest.mark.asyncio
async def test_gemini_empty_response_uses_local_guidance() -> None:
    """Verify empty model output does not produce a blank document explanation."""
    settings = MagicMock(gemini_api_key="test", gemini_model="gemini-2.5-flash")
    with patch("app.services.gemini_service.get_settings", return_value=settings):
        with patch("google.genai.Client") as client_class:
            client_class.return_value.models.generate_content.return_value = MagicMock(text=" ")
            response = await explain_document_image(b"image", "image/jpeg")
    assert "फोटो" in response.summary_hi


@pytest.mark.asyncio
async def test_speech_service_mock_client() -> None:
    """Test Google Cloud Speech client mock."""
    mock_result = MagicMock()
    mock_alt = MagicMock()
    mock_alt.transcript = "मेरी आवाज़ सुनो"
    mock_alt.confidence = 0.95
    mock_result.alternatives = [mock_alt]

    mock_resp = MagicMock()
    mock_resp.results = [mock_result]

    with patch("app.services.speech_service.get_settings") as speech_settings:
        speech_settings.return_value.app_env = "production"
        speech_settings.return_value.gcp_project_id = "test"
        with patch("google.cloud.speech.SpeechClient") as mock_speech_cls:
            mock_speech = MagicMock()
            mock_speech.recognize.return_value = mock_resp
            mock_speech_cls.return_value = mock_speech

            trans = await transcribe_audio(b"audio-bytes", content_type="audio/webm")
            assert trans.text == "मेरी आवाज़ सुनो"
            mock_speech.recognize.assert_called_once()
            assert mock_speech.recognize.call_args.kwargs["timeout"] == 5.0


@pytest.mark.asyncio
async def test_speech_formats_empty_result_and_service_error() -> None:
    """Cover WAV/OGG encoding, empty recognition, and Speech fallback cases."""
    from google.cloud import speech

    settings = MagicMock(app_env="production", gcp_project_id="test")
    empty = MagicMock(results=[])
    cloud_client = MagicMock()
    cloud_client.recognize.side_effect = [empty, empty, TimeoutError]
    with patch("app.services.speech_service.get_settings", return_value=settings):
        with patch("google.cloud.speech.SpeechClient", return_value=cloud_client):
            wav = await transcribe_audio(b"wav", "audio/wav")
            ogg = await transcribe_audio(b"ogg", "audio/ogg")
            failed = await transcribe_audio(b"webm", "audio/webm")
    calls = cloud_client.recognize.call_args_list
    assert calls[0].kwargs["config"].encoding == speech.RecognitionConfig.AudioEncoding.LINEAR16
    assert calls[1].kwargs["config"].encoding == speech.RecognitionConfig.AudioEncoding.OGG_OPUS
    assert wav.confidence == ogg.confidence == 0.8
    assert failed.confidence == 0.8
    assert all(call.kwargs["timeout"] == 5.0 for call in calls)


@pytest.mark.asyncio
async def test_tts_service_mock_client() -> None:
    """Test Google Cloud TTS client mock."""
    mock_resp = MagicMock()
    mock_resp.audio_content = b"\xff\xfb\x90fake-synthesized-audio"

    with patch("google.cloud.texttospeech.TextToSpeechClient") as mock_tts_cls:
        mock_tts = MagicMock()
        mock_tts.synthesize_speech.return_value = mock_resp
        mock_tts_cls.return_value = mock_tts

        audio = await synthesize_speech("नया परीक्षण वाक्य 123", voice_name="hi-IN-Neural2-A")
        assert audio == b"\xff\xfb\x90fake-synthesized-audio"
        assert mock_tts.synthesize_speech.call_args.kwargs["timeout"] == 5.0


def test_secret_manager_cloud_api_mock() -> None:
    """Test Secret Manager access uses a request deadline and returns its payload."""
    with patch("google.cloud.secretmanager.SecretManagerServiceClient") as client_class:
        client = MagicMock()
        client.access_secret_version.return_value.payload.data = b"test-value"
        client_class.return_value = client

        assert load_secret_from_gcp("TEST_SECRET", "test") == "test-value"
        assert client.access_secret_version.call_args.kwargs["timeout"] == 5.0


@pytest.mark.asyncio
async def test_tts_failure_returns_browser_fallback_signal() -> None:
    """Test TTS service failures return no audio so clients use browser speech."""
    with patch("google.cloud.texttospeech.TextToSpeechClient") as client_class:
        client = MagicMock()
        client.synthesize_speech.side_effect = TimeoutError
        client_class.return_value = client

        audio = await synthesize_speech("विफलता परीक्षण वाक्य")

    assert audio is None
