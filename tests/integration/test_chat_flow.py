"""Integration test for multi-turn chat conversation flow with fallback."""

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_chat_multi_turn_flow(client: AsyncClient) -> None:
    """Verify complete 5-turn conversational flow executes deterministically."""
    session_id = "test-session-uuid-1234"
    turns = [
        ("नमस्ते", "ASK_YES_NO", ""),
        ("हाँ मैं गर्भवती हूँ", "ASK_CHOICE", "पहली"),
        ("पहली संतान", "ASK_CHOICE", "राशन कार्ड"),
        ("राशन कार्ड है", "ASK_YES_NO", "सरकारी"),
        ("नहीं, कोई नौकरी नहीं है", "SHOW_RESULT", "5,000"),
    ]
    responses = []
    for message, expected_action, phrase in turns:
        response = await client.post(
            "/api/v1/chat",
            json={"session_id": session_id, "message": message, "locale": "hi"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["ui_action"] == expected_action
        assert phrase in data["speech_text"]
        responses.append(data)

    final = responses[-1]
    assert final["data"]["eligible"] is True
    assert final["data"]["benefit_amount_inr"] == 5000
