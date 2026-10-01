"""Endpoints for Paper Whisperer (Vision) and Practice Mode (Rehearsal)."""

from fastapi import APIRouter, File, HTTPException, Request, UploadFile

from app.core.config import get_settings
from app.core.rate_limit import limiter
from app.core.security import sanitize_text
from app.models.vision import DocumentExplainResponse, PracticeRequest, PracticeResponse
from app.services.gemini_service import explain_document_image

router = APIRouter(prefix="/api/v1", tags=["Vision & Practice"])

MAX_IMAGE_SIZE_BYTES = 5 * 1024 * 1024  # 5 MB
ALLOWED_IMAGE_TYPES = {"image/jpeg", "image/png", "image/webp"}


@router.post("/vision/explain", response_model=DocumentExplainResponse)
@limiter.limit(get_settings().rate_limit_vision)
async def explain_document(
    request: Request,
    file: UploadFile = File(...),
) -> DocumentExplainResponse:
    """Summarize a government document photo with Gemini or localized fallback.

    Images stay in memory locally and are sent to Gemini when the API key is configured.
    """
    content_type = file.content_type or ""
    if content_type.lower() not in ALLOWED_IMAGE_TYPES:
        raise HTTPException(
            status_code=415,
            detail="केवल JPEG, PNG या WebP फ़ोटो स्वीकार्य हैं।",
        )

    content = await file.read()
    if len(content) > MAX_IMAGE_SIZE_BYTES:
        raise HTTPException(status_code=413, detail="फ़ोटो 5 MB से कम होनी चाहिए।")

    return await explain_document_image(content, content_type.lower())


@router.post("/practice", response_model=PracticeResponse)
@limiter.limit(get_settings().rate_limit_chat)
async def practice_rehearsal(
    request: Request,
    body: PracticeRequest,
) -> PracticeResponse:
    """Rehearse visiting the Anganwadi Centre with an encouraging role-play partner."""
    clean_text = sanitize_text(body.user_utterance)

    return PracticeResponse(
        officer_reply_hi=f"नमस्ते दीदी! आइए बैठिए। आपने कहा: '{clean_text}'। बिल्कुल सही! हम आपका फॉर्म भर देंगे।",
        coaching_tip_hi="दीदी, आपने बहुत अच्छे से बात की! आंगनवाड़ी जाते समय अपना आधार कार्ड और बैंक पासबुक साथ ले जाना न भूलें।",
    )
