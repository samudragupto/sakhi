"""Google Maps Places API (New) integration with privacy-first coordinate rounding."""

from math import asin, cos, radians, sin, sqrt
from typing import Any

import httpx

from app.core.config import get_settings
from app.core.logging import logger
from app.models.places import AnganwadiCentre, NearbyPlacesResponse

FALLBACK_MESSAGE = "अपने गाँव के निकटतम आंगनवाड़ी केंद्र या ग्राम पंचायत भवन में आशा दीदी से संपर्क करें।"


def round_coordinates(lat: float, lng: float) -> tuple[float, float]:
    """Round coordinates to 2 decimal places (~1.1 km precision) to protect user location privacy."""
    return round(lat, 2), round(lng, 2)


def _distance_km(start_lat: float, start_lng: float, end_lat: float, end_lng: float) -> float:
    """Calculate straight-line distance between two coordinates in kilometers."""
    lat_delta = radians(end_lat - start_lat)
    lng_delta = radians(end_lng - start_lng)
    value = (
        sin(lat_delta / 2) ** 2
        + cos(radians(start_lat)) * cos(radians(end_lat)) * sin(lng_delta / 2) ** 2
    )
    return 6371 * 2 * asin(sqrt(value))


def _parse_places(data: dict[str, Any], lat: float, lng: float) -> list[AnganwadiCentre]:
    """Convert Places API results into the app’s public centre model."""
    centres = []
    maps_url = f"https://www.google.com/maps/search/?api=1&query={lat},{lng}"
    for place in data.get("places", []):
        name = place.get("displayName", {}).get("text", "आंगनवाड़ी केंद्र")
        address = place.get("formattedAddress", "ग्राम पंचायत")
        try:
            place_lat = float(place["location"]["latitude"])
            place_lng = float(place["location"]["longitude"])
        except (KeyError, TypeError, ValueError):
            continue
        maps_url = f"https://www.google.com/maps/search/?api=1&query={place_lat},{place_lng}"
        centres.append(
            AnganwadiCentre(
                name=name,
                address=address,
                distance_km=round(_distance_km(lat, lng, place_lat, place_lng), 1),
                maps_url=maps_url,
            )
        )
    return centres


def _places_request_body(lat: float, lng: float) -> dict[str, Any]:
    """Build the minimal privacy-rounded Places API request body."""
    return {
        "textQuery": "Anganwadi Centre OR Common Service Centre",
        "locationBias": {
            "circle": {
                "center": {"latitude": lat, "longitude": lng},
                "radius": 5000.0,
            }
        },
        "maxResultCount": 3,
    }


async def find_nearby_centres(lat: float, lng: float) -> NearbyPlacesResponse:
    """Find nearest Anganwadi Centres using Places API (New) or mock fallback."""
    clean_lat, clean_lng = round_coordinates(lat, lng)
    settings = get_settings()

    if not settings.google_maps_api_key:
        return _get_fallback_centres(clean_lat, clean_lng)

    url = "https://places.googleapis.com/v1/places:searchText"
    headers = {
        "Content-Type": "application/json",
        "X-Goog-Api-Key": settings.google_maps_api_key,
        "X-Goog-FieldMask": "places.displayName,places.formattedAddress,places.location",
    }
    body = _places_request_body(clean_lat, clean_lng)

    try:
        async with httpx.AsyncClient(timeout=4.0) as client:
            resp = await client.post(url, json=body, headers=headers)
            if resp.status_code == 200:
                centres = _parse_places(resp.json(), clean_lat, clean_lng)
                if centres:
                    return NearbyPlacesResponse(
                        centres=centres, fallback_message_hi=FALLBACK_MESSAGE
                    )
    except Exception:
        logger.warning(
            "Maps Places query failed, returning fallback centres",
            extra={"event": "maps_fallback"},
        )

    return _get_fallback_centres(clean_lat, clean_lng)


def _get_fallback_centres(lat: float, lng: float) -> NearbyPlacesResponse:
    """Generate generic trusted rural centres when Maps API is offline."""
    default_centres = [
        AnganwadiCentre(
            name="ग्राम पंचायत आंगनवाड़ी केंद्र (मुख्य)",
            address="पंचायत भवन के पास",
            distance_km=0.8,
            maps_url=f"https://www.google.com/maps/search/?api=1&query={lat},{lng}",
        ),
        AnganwadiCentre(
            name="प्राथमिक स्वास्थ्य उप-केंद्र (HWC / Sub-Centre)",
            address="गाँव के प्राथमिक विद्यालय के सामने",
            distance_km=1.5,
            maps_url=f"https://www.google.com/maps/search/?api=1&query={lat},{lng}",
        ),
        AnganwadiCentre(
            name="कॉमन सर्विस सेंटर (CSC Digital Seva)",
            address="मुख्य बाज़ार चौराहा",
            distance_km=2.1,
            maps_url=f"https://www.google.com/maps/search/?api=1&query={lat},{lng}",
        ),
    ]
    return NearbyPlacesResponse(centres=default_centres, fallback_message_hi=FALLBACK_MESSAGE)
