"""Integration tests for Paper Whisperer (Vision) and Practice Mode endpoints."""

from unittest.mock import MagicMock, patch

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_vision_explain_success(client: AsyncClient) -> None:
    """Verify /api/v1/vision/explain returns a mocked Gemini summary."""
    fake_img = b"\xff\xd8\xff\xe0\x00\x10JFIFfakeimagedata"
    response = MagicMock(text="इस पत्र में आवेदन की तारीख दी गई है।")
    with patch("app.services.gemini_service.get_settings") as settings:
        settings.return_value.gemini_api_key = "test"
        settings.return_value.gemini_model = "gemini-2.5-flash"
        with patch("google.genai.Client") as client_class:
            cloud_client = MagicMock()
            cloud_client.models.generate_content.return_value = response
            client_class.return_value = cloud_client
            res = await client.post(
                "/api/v1/vision/explain",
                files={"file": ("letter.jpg", fake_img, "image/jpeg")},
            )
    assert res.status_code == 200
    data = res.json()
    assert "आवेदन" in data["summary_hi"]
    assert "आंगनवाड़ी" in data["what_to_do_hi"]


@pytest.mark.asyncio
async def test_vision_explain_invalid_mime(client: AsyncClient) -> None:
    """Verify unsupported file type returns 415."""
    res = await client.post(
        "/api/v1/vision/explain",
        files={"file": ("doc.pdf", b"%PDF-1.4...", "application/pdf")},
    )
    assert res.status_code == 415


@pytest.mark.asyncio
async def test_vision_explain_rejects_oversized_image(client: AsyncClient) -> None:
    """Verify images above the 5 MB upload limit are rejected before inference."""
    image = bytes(5 * 1024 * 1024 + 1)
    response = await client.post(
        "/api/v1/vision/explain",
        files={"file": ("large.jpg", image, "image/jpeg")},
    )
    assert response.status_code == 413


@pytest.mark.asyncio
async def test_practice_mode_endpoint(client: AsyncClient) -> None:
    """Verify /api/v1/practice gives courteous roleplay response and coaching tip."""
    res = await client.post(
        "/api/v1/practice",
        json={"user_utterance": "नमस्ते दीदी, मुझे मातृ वंदना के पैसे के लिए फॉर्म भरना है।"},
    )
    assert res.status_code == 200
    data = res.json()
    assert "नमस्ते दीदी" in data["officer_reply_hi"]
    assert "कोचिंग" not in data["officer_reply_hi"]  # Ensure no meta leaking
    assert "आधार कार्ड" in data["coaching_tip_hi"]
