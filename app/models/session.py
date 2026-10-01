"""Session data structures for Firestore anonymous tracking."""

from datetime import UTC, datetime
from typing import Any

from pydantic import BaseModel, Field


class SessionDoc(BaseModel):
    """Anonymous user session document with TTL."""

    session_id: str
    step: int = 1
    answers: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    expire_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
