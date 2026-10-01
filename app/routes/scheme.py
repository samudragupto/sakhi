"""Endpoints for scheme metadata and direct eligibility calculation."""

from typing import Any

from fastapi import APIRouter

from app.models.eligibility import EligibilityAnswers, EligibilityResult
from app.services.eligibility import check_pmmvy_eligibility, load_scheme_data

router = APIRouter(prefix="/api/v1", tags=["Scheme & Eligibility"])


@router.get("/scheme")
async def get_scheme_info() -> dict[str, Any]:
    """Return PMMVY scheme details, rules, benefits, and documents."""
    return load_scheme_data("pmmvy")


@router.post("/eligibility", response_model=EligibilityResult)
async def evaluate_eligibility(answers: EligibilityAnswers) -> EligibilityResult:
    """Deterministically evaluate applicant eligibility for PMMVY."""
    return check_pmmvy_eligibility(answers)
