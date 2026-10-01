"""Pydantic models for deterministic PMMVY eligibility evaluation."""

from enum import StrEnum
from typing import Any, Literal

from pydantic import BaseModel, Field


class EligibilityCategory(StrEnum):
    """Eligible categories under PMMVY 2.0 Mission Shakti rules."""

    SC_ST = "SC_ST"
    DISABILITY_40_PLUS = "DISABILITY_40_PLUS"
    BPL_RATION_CARD = "BPL_RATION_CARD"
    AYUSHMAN_PMJAY = "AYUSHMAN_PMJAY"
    E_SHRAM = "E_SHRAM"
    PM_KISAN = "PM_KISAN"
    MGNREGA = "MGNREGA"
    INCOME_BELOW_8_LAKH = "INCOME_BELOW_8_LAKH"
    AWW_AWH_ASHA = "AWW_AWH_ASHA"


class EligibilityAnswers(BaseModel):
    """User answers needed to determine PMMVY eligibility."""

    is_pregnant_or_lactating: bool = Field(
        ...,
        description="Whether the applicant is currently pregnant or lactating mother",
    )
    child_number: Literal[1, 2] = Field(
        ...,
        description="Child index (1 for first child, 2 for second child)",
    )
    second_child_is_girl: bool | None = Field(
        default=None,
        description="Must be true if child_number == 2 for PMMVY benefits",
    )
    categories: list[EligibilityCategory] = Field(
        default_factory=list,
        description="List of qualifying socioeconomic or welfare categories",
    )
    is_govt_or_psu_employee: bool = Field(
        ...,
        description="Whether applicant or spouse is regular govt or PSU employee",
    )


class InstallmentDetail(BaseModel):
    """Detailed installment breakdown."""

    installment_number: int
    amount_inr: int
    condition_hi: str
    condition_key: str


class EligibilityResult(BaseModel):
    """Deterministic result computed by pure Python rules engine."""

    eligible: bool
    benefit_amount_inr: int
    installments: list[InstallmentDetail]
    reason_code: str
    reason_hi: str
    required_documents: list[str]
    next_steps: list[str]
    metadata: dict[str, Any] = Field(default_factory=dict)
