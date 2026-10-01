"""Conversational chat endpoint for Sakhi."""

from fastapi import APIRouter, Request

from app.core.config import get_settings
from app.core.rate_limit import limiter
from app.core.security import sanitize_text
from app.models.chat import ChatRequest, ChatResponse
from app.services.gemini_service import process_chat
from app.services.session_service import get_or_create_session, update_session

router = APIRouter(prefix="/api/v1", tags=["Chat"])


@router.post("/chat", response_model=ChatResponse)
@limiter.limit(get_settings().rate_limit_chat)
async def chat_interaction(request: Request, body: ChatRequest) -> ChatResponse:
    """Conversational endpoint handling voice or text inquiries with fallback."""
    cleaned_msg = sanitize_text(body.message)
    session = await get_or_create_session(body.session_id)
    response = await process_chat(cleaned_msg, session)
    await update_session(session)
    return response
