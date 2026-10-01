"""Exhaustive tests for the deterministic PMMVY 2.0 eligibility engine.

Tests all categories, exclusions, second child logic, and edge cases.
"""

from pathlib import Path

import pytest
from pydantic import ValidationError

from app.models.eligibility import EligibilityAnswers, EligibilityCategory
from app.services.eligibility import (
    check_pmmvy_eligibility,
    load_locale_data,
    load_scheme_data,
)


def test_scheme_json_loads_correctly() -> None:
    """Ensure scheme json exists and contains expected metadata."""
    data = load_scheme_data("pmmvy")
    assert data["scheme_id"] == "pmmvy"
    assert "Mission Shakti" in data["version"]
    assert len(data["eligible_categories"]) == 9


def test_first_child_eligible_all_categories() -> None:
    """Verify first child eligibility across every qualifying category."""
    for cat in EligibilityCategory:
        answers = EligibilityAnswers(
            is_pregnant_or_lactating=True,
            child_number=1,
            second_child_is_girl=None,
            categories=[cat],
            is_govt_or_psu_employee=False,
        )
        res = check_pmmvy_eligibility(answers)
        assert res.eligible is True
        assert res.benefit_amount_inr == 5000
        assert len(res.installments) == 2
        assert res.installments[0].amount_inr == 3000
        assert res.installments[1].amount_inr == 2000
        assert res.reason_code == "ELIGIBLE_FIRST_CHILD"
        assert "aadhaar_mother" in res.required_documents
        assert "birth_certificate" not in res.required_documents


def test_second_child_girl_eligible() -> None:
    """Verify second child is eligible for ₹6,000 if girl."""
    answers = EligibilityAnswers(
        is_pregnant_or_lactating=True,
        child_number=2,
        second_child_is_girl=True,
        categories=[EligibilityCategory.BPL_RATION_CARD],
        is_govt_or_psu_employee=False,
    )
    res = check_pmmvy_eligibility(answers)
    assert res.eligible is True
    assert res.benefit_amount_inr == 6000
    assert len(res.installments) == 1
    assert res.installments[0].amount_inr == 6000
    assert res.reason_code == "ELIGIBLE_SECOND_CHILD_GIRL"
    assert "birth_certificate" in res.required_documents


def test_second_child_boy_ineligible() -> None:
    """Verify second child is ineligible if not a girl."""
    answers = EligibilityAnswers(
        is_pregnant_or_lactating=True,
        child_number=2,
        second_child_is_girl=False,
        categories=[EligibilityCategory.E_SHRAM],
        is_govt_or_psu_employee=False,
    )
    res = check_pmmvy_eligibility(answers)
    assert res.eligible is False
    assert res.benefit_amount_inr == 0
    assert res.reason_code == "INELIGIBLE_SECOND_CHILD_BOY"


def test_govt_employee_excluded() -> None:
    """Verify government/PSU employee exclusion takes precedence."""
    answers = EligibilityAnswers(
        is_pregnant_or_lactating=True,
        child_number=1,
        second_child_is_girl=None,
        categories=[EligibilityCategory.SC_ST],
        is_govt_or_psu_employee=True,
    )
    res = check_pmmvy_eligibility(answers)
    assert res.eligible is False
    assert res.reason_code == "INELIGIBLE_GOVT_EMPLOYEE"


def test_not_pregnant_or_lactating_ineligible() -> None:
    """Verify non-pregnant, non-lactating user is ineligible."""
    answers = EligibilityAnswers(
        is_pregnant_or_lactating=False,
        child_number=1,
        second_child_is_girl=None,
        categories=[EligibilityCategory.MGNREGA],
        is_govt_or_psu_employee=False,
    )
    res = check_pmmvy_eligibility(answers)
    assert res.eligible is False
    assert res.reason_code == "INELIGIBLE_NOT_PREGNANT_LACTATING"


def test_no_category_ineligible() -> None:
    """Verify applicant with no eligible welfare categories is ineligible."""
    answers = EligibilityAnswers(
        is_pregnant_or_lactating=True,
        child_number=1,
        second_child_is_girl=None,
        categories=[],
        is_govt_or_psu_employee=False,
    )
    res = check_pmmvy_eligibility(answers)
    assert res.eligible is False
    assert res.reason_code == "INELIGIBLE_NO_CATEGORY"


def test_invalid_child_number_rejected_by_model() -> None:
    """Ensure invalid child numbers like 3 trigger ValidationError."""
    with pytest.raises(ValidationError):
        EligibilityAnswers(
            is_pregnant_or_lactating=True,
            child_number=3,  # type: ignore
            categories=[EligibilityCategory.SC_ST],
            is_govt_or_psu_employee=False,
        )


def test_missing_scheme_and_locale_files_raise(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Verify missing scheme and locale JSON files fail explicitly."""
    monkeypatch.setattr("app.services.eligibility.SCHEMES_DIR", tmp_path)
    monkeypatch.setattr("app.services.eligibility.LOCALES_DIR", tmp_path)
    with pytest.raises(FileNotFoundError):
        load_scheme_data("missing")
    with pytest.raises(FileNotFoundError):
        load_locale_data("missing")
