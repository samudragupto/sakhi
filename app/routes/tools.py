"""Endpoints for nearby centres, officer card, and session deletion."""

from fastapi import APIRouter, Query, Request

from app.core.config import get_settings
from app.core.rate_limit import limiter
from app.models.card import OfficerCardData, OfficerCardRequest
from app.models.places import NearbyPlacesResponse
from app.services.card_service import generate_officer_card
from app.services.maps_service import find_nearby_centres
from app.services.session_service import delete_session

router = APIRouter(prefix="/api/v1", tags=["Civic Tools & Privacy"])


@router.get("/places/nearby", response_model=NearbyPlacesResponse)
@limiter.limit(get_settings().rate_limit_default)
async def get_nearby_anganwadis(
    request: Request,
    lat: float = Query(..., ge=-90.0, le=90.0),
    lng: float = Query(..., ge=-180.0, le=180.0),
) -> NearbyPlacesResponse:
    """Find nearby Anganwadi Centres and CSCs with privacy coordinate rounding."""
    return await find_nearby_centres(lat, lng)


@router.post("/card", response_model=OfficerCardData)
async def create_officer_card(body: OfficerCardRequest) -> OfficerCardData:
    """Generate bilingual officer presentation card with official scheme QR code."""
    return generate_officer_card(body)


@router.delete("/session")
async def erase_session(session_id: str = Query(..., min_length=4)) -> dict[str, str]:
    """Wipe anonymous session data instantly for shared phone privacy."""
    await delete_session(session_id)
    return {"status": "deleted", "message": "सत्र की सभी जानकारी सफलतापूर्वक मिटा दी गई है।"}
