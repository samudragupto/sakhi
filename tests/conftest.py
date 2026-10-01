"""Shared pytest fixtures and test configurations."""

from collections.abc import AsyncIterator

import pytest
from httpx import ASGITransport, AsyncClient

from app.main import create_app


@pytest.fixture(autouse=True)
def _reset_gemini_client() -> None:  # type: ignore[misc]
    """Reset cached Gemini client between tests for isolation."""
    import app.services.gemini_service as gs

    gs._CACHED_GENAI_CLIENT = None


@pytest.fixture
def anyio_backend() -> str:
    """Configure anyio backend for asyncio."""
    return "asyncio"


@pytest.fixture
async def client() -> AsyncIterator[AsyncClient]:
    """Provide AsyncClient for test suite."""
    app = create_app()
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://testserver") as ac:
        yield ac
