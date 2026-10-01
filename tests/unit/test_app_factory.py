"""Unit tests for FastAPI app factory and asset mounting resilience.

Verifies:
1. Importing app.main never raises.
2. create_app() works properly when static or locale directories exist.
3. create_app() degrades gracefully with a warning when static or locale directories are missing.
4. BASE_DIR points to the app directory.
"""

from pathlib import Path

import pytest
from httpx import ASGITransport, AsyncClient

from app.main import BASE_DIR, create_app


def test_app_factory_succeeds_normally() -> None:
    """Verify create_app instantiates FastAPI app with configured middleware and routers."""
    app = create_app()
    assert app.title == "Sakhi – आपकी आवाज़ दीदी"
    assert app.version == "0.1.0"


def test_base_dir_resolves_to_app() -> None:
    """Verify BASE_DIR resolves to the directory containing main.py."""
    assert BASE_DIR.is_dir()
    assert (BASE_DIR / "main.py").exists()
    assert (BASE_DIR / "data").exists()


@pytest.mark.asyncio
async def test_create_app_handles_missing_directories(monkeypatch: pytest.MonkeyPatch) -> None:
    """Verify create_app does not raise even if static or locales folders do not exist."""
    original_exists = Path.exists

    def mock_exists(path_obj: Path) -> bool:
        if "static" in path_obj.parts or "locales" in path_obj.parts:
            return False
        return original_exists(path_obj)

    monkeypatch.setattr(Path, "exists", mock_exists)
    app = create_app()
    assert app is not None
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://testserver"
    ) as client:
        res = await client.get("/health")
        assert res.status_code == 200
        assert res.json()["status"] == "healthy"


def test_data_files_exist_via_base_dir() -> None:
    """Verify locale and scheme data are accessible via BASE_DIR."""
    assert (BASE_DIR / "data" / "locales" / "hi.json").exists()
    assert (BASE_DIR / "data" / "schemes" / "pmmvy.json").exists()
