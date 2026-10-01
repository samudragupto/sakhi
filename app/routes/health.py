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
        "app_env": settings.app_env,
        "uptime_seconds": uptime_seconds,
        "version": "0.1.0",
    }
