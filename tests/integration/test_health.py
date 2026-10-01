"""Integration test for /health endpoint."""

from pathlib import Path
from unittest.mock import patch

import pytest
from fastapi import FastAPI, Request
from httpx import AsyncClient

from app.main import _handle_global_exception, _mount_assets, create_app, lifespan


@pytest.mark.asyncio
async def test_health_check_returns_200(client: AsyncClient) -> None:
    """Verify /health endpoint returns healthy status and metadata."""
    response = await client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert "Sakhi" in data["app_name"]
    assert "uptime_seconds" in data
    assert data["version"] == "0.1.0"


@pytest.mark.asyncio
async def test_application_lifespan_emits_start_and_shutdown_events() -> None:
    """Verify lifespan emits only allowlisted startup and shutdown events."""
    with patch("app.main.logger.info") as log_info:
        async with lifespan(create_app()):
            pass
    events = [call.kwargs["extra"]["event"] for call in log_info.call_args_list]
    assert events == ["startup", "shutdown"]


@pytest.mark.asyncio
async def test_global_error_handler_hides_exception_content() -> None:
    """Verify global error responses are generic and do not log exception text."""
    request = Request(
        {"type": "http", "method": "GET", "path": "/", "headers": [], "query_string": b""}
    )
    with patch("app.main.logger.error") as log_error:
        response = await _handle_global_exception(request, ValueError("PII 9876543210"))
    assert response.status_code == 500
    assert b"InternalServerError" in response.body
    assert "9876543210" not in str(log_error.call_args)


def _static_directory_missing(path: Path) -> bool:
    """Make only the frontend static directory appear absent for route testing."""
    return path.name != "static"


def test_mount_assets_handles_missing_static_directory(monkeypatch: pytest.MonkeyPatch) -> None:
    """Verify locale mounting remains available when static assets are absent."""
    monkeypatch.setattr("app.main.Path.exists", _static_directory_missing)
    app = FastAPI()
    _mount_assets(app)
    assert not any(route.path == "/static" for route in app.routes)
    assert any(route.path == "/locales" for route in app.routes)
