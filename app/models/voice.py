"""Pydantic models for voice STT and TTS services."""

from pydantic import BaseModel, Field


class TranscribeResponse(BaseModel):
    """Voice transcription result."""

    text: str = Field(..., description="Recognized speech text in Hindi")
    confidence: float = Field(default=1.0, description="Recognition confidence score")
    language: str = Field(default="hi-IN", description="Language code")


class SpeakRequest(BaseModel):
    """Text-to-speech synthesis request."""

    text: str = Field(..., max_length=1000, description="Hindi text to be synthesized")
    language: str = Field(default="hi-IN", description="Language code")
    speaking_rate: float = Field(default=0.9, ge=0.5, le=1.5, description="Paced speaking rate")
