"""Main application factory, middleware configuration, and router aggregation."""

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded

from app.core.config import Settings, get_settings
from app.core.logging import logger, setup_logging
from app.core.rate_limit import limiter
from app.core.security import SecurityHeadersMiddleware
from app.routes.chat import router as chat_router
from app.routes.health import router as health_router
from app.routes.scheme import router as scheme_router
from app.routes.tools import router as tools_router
from app.routes.vision import router as vision_router
from app.routes.voice import router as voice_router


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """Lifespan context manager for startup and shutdown events."""
    from app.services.gemini_service import get_gemini_client

    get_gemini_client()
    logger.info(
        "Application starting up",
        extra={"event": "startup"},
    )
    yield
    logger.info("Application shutting down", extra={"event": "shutdown"})


async def _handle_global_exception(request: Request, exc: Exception) -> JSONResponse:
    """Return a generic Hindi response without logging request or exception content."""
    logger.error(
        "Unhandled exception occurred",
        extra={"event": "error"},
    )
    return JSONResponse(
        status_code=500,
        content={
            "error": "InternalServerError",
            "message": "सेवा में समस्या आ रही है। कृपया थोड़ी देर बाद पुनः प्रयास करें।",
        },
    )


def _add_middleware(app: FastAPI, settings: Settings) -> None:
    """Register security and transport middleware in the required order."""
    app.add_middleware(SecurityHeadersMiddleware)
    app.add_middleware(GZipMiddleware, minimum_size=1000)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.allowed_origins,
        allow_credentials=True,
        allow_methods=["GET", "POST", "DELETE", "OPTIONS"],
        allow_headers=["*"],
    )
    app.add_middleware(
        TrustedHostMiddleware,
        allowed_hosts=settings.trusted_hosts,
    )


def _add_routers(app: FastAPI) -> None:
    """Register application API routers."""
    app.include_router(health_router)
    app.include_router(scheme_router)
    app.include_router(chat_router)
    app.include_router(voice_router)
    app.include_router(tools_router)
    app.include_router(vision_router)


BASE_DIR = Path(__file__).resolve().parent


def _mount_assets(app: FastAPI) -> None:
    """Mount frontend assets and locale files if they exist; warn otherwise."""
    static_dir = BASE_DIR / "static"
    if static_dir.exists():
        app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")
    else:
        logger.warning(
            "Static directory missing; frontend static files not mounted",
            extra={"event": "missing_static_dir"},
        )

    locale_dir = BASE_DIR / "data" / "locales"
    if locale_dir.exists():
        app.mount("/locales", StaticFiles(directory=str(locale_dir)), name="locales")
    else:
        logger.warning(
            "Locale directory missing; /locales endpoint not mounted",
            extra={"event": "missing_locale_dir"},
        )


def create_app() -> FastAPI:
    """Instantiate and configure the FastAPI application."""
    settings = get_settings()
    setup_logging(settings.log_level)
    app = FastAPI(
        title=settings.app_name,
        description="Sakhi – आपकी आवाज़ दीदी: Accessible Voice-First Civic Assistant",
        version="0.1.0",
        debug=settings.debug,
        lifespan=lifespan,
    )
    app.state.limiter = limiter
    app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)  # type: ignore
    app.add_exception_handler(Exception, _handle_global_exception)
    _add_middleware(app, settings)
    _add_routers(app)
    _mount_assets(app)
    return app


app = create_app()
