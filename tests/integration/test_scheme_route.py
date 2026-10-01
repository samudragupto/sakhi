"""Integration tests for scheme and eligibility endpoints."""

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_get_scheme_metadata(client: AsyncClient) -> None:
    """Verify /api/v1/scheme returns PMMVY data."""
    res = await client.get("/api/v1/scheme")
    assert res.status_code == 200
    data = res.json()
    assert data["scheme_id"] == "pmmvy"
    assert "benefits" in data


@pytest.mark.asyncio
async def test_post_eligibility_endpoint_success(client: AsyncClient) -> None:
    """Verify /api/v1/eligibility returns deterministic calculation."""
    payload = {
        "is_pregnant_or_lactating": True,
        "child_number": 1,
        "second_child_is_girl": None,
        "categories": ["BPL_RATION_CARD"],
        "is_govt_or_psu_employee": False,
    }
    res = await client.post("/api/v1/eligibility", json=payload)
    assert res.status_code == 200
    data = res.json()
    assert data["eligible"] is True
    assert data["benefit_amount_inr"] == 5000
    assert data["reason_code"] == "ELIGIBLE_FIRST_CHILD"
