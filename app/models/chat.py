"""Data models for conversational chat interactions."""

from enum import StrEnum
from typing import Any

from pydantic import BaseModel, Field


class UIAction(StrEnum):
    """UI actions communicated to frontend."""

    ASK_YES_NO = "ASK_YES_NO"
    ASK_CHOICE = "ASK_CHOICE"
    SHOW_RESULT = "SHOW_RESULT"
    NONE = "NONE"


class QuickReply(BaseModel):
    """Quick reply button suggestion."""

    label_hi: str
    value: str


class ChatRequest(BaseModel):
    """Incoming user chat message."""

    session_id: str = Field(..., description="Anonymous UUID4 session identifier")
    message: str = Field(..., max_length=500, description="User transcribed or typed message")


class ChatResponse(BaseModel):
    """Structured response for voice and visual rendering."""

    speech_text: str = Field(..., description="Spoken Hindi sentence for TTS")
    caption: str = Field(..., description="Live visual captions for the user")
    ui_action: UIAction = Field(default=UIAction.NONE, description="Frontend trigger action")
    quick_replies: list[QuickReply] = Field(default_factory=list, description="Actionable buttons")
    data: dict[str, Any] = Field(
        default_factory=dict, description="Payload (e.g. eligibility data)"
    )
