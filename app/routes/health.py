"""Health and readiness check endpoints."""

import time
from typing import Any

from fastapi import APIRouter

from app.core.config import get_settings

router = APIRouter(tags=["Health"])
START_TIME = time.time()


@router.get("/health")
async def health_check() -> dict[str, Any]:
    """Return health status, environment, uptime, and version."""
    settings = get_settings()
    uptime_seconds = int(time.time() - START_TIME)
    return {
        "status": "healthy",
        "app_name": settings.app_name,
        "environment": settings.environment,
        "uptime_seconds": uptime_seconds,
        "version": "0.1.0",
    }


@router.get("/health/ready")
async def readiness_check() -> dict[str, Any]:
    """Report per-service readiness without revealing configuration values."""
    settings = get_settings()
    return {
        "status": "ready",
        "services": {
            "gemini": bool(settings.google_cloud_project),
            "maps": bool(settings.maps_api_key),
            "firestore": bool(settings.google_cloud_project),
            "speech": bool(settings.google_cloud_project),
            "tts": bool(settings.google_cloud_project),
            "translation": bool(settings.google_cloud_project),
        },
    }
