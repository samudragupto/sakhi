"""Data models for nearest Anganwadi Centres and Common Service Centres."""

from pydantic import BaseModel, Field


class AnganwadiCentre(BaseModel):
    """Details of nearby Anganwadi or CSC centre."""

    name: str = Field(..., description="Name of the Anganwadi / Centre")
    address: str = Field(..., description="Village or ward address")
    distance_km: float = Field(..., description="Approximate distance in kilometers")
    maps_url: str = Field(..., description="Google Maps navigation link")


class NearbyPlacesResponse(BaseModel):
    """Response containing nearest Anganwadi centres."""

    centres: list[AnganwadiCentre]
    fallback_message_hi: str
