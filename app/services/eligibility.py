"""Deterministic PMMVY 2.0 eligibility rules engine.

Pure Python implementation. Never relies on LLMs for calculations or decisions.
Reads scheme rules from externalized data/schemes/pmmvy.json.
"""

import json
from functools import lru_cache
from pathlib import Path
from typing import Any

from app.models.eligibility import (
    EligibilityAnswers,
    EligibilityResult,
    InstallmentDetail,
)

SCHEMES_DIR = Path(__file__).resolve().parent.parent / "data" / "schemes"
LOCALES_DIR = Path(__file__).resolve().parent.parent / "data" / "locales"


@lru_cache
def load_scheme_data(scheme_id: str = "pmmvy") -> dict[str, Any]:
    """Load and cache scheme rules definition from JSON."""
    file_path = SCHEMES_DIR / f"{scheme_id}.json"
    if not file_path.exists():
        raise FileNotFoundError(f"Scheme file not found: {file_path}")
    with open(file_path, encoding="utf-8") as f:
        data: dict[str, Any] = json.load(f)
        return data


@lru_cache
def load_locale_data(lang: str = "hi") -> dict[str, Any]:
    """Load and cache localization strings from JSON."""
    file_path = LOCALES_DIR / f"{lang}.json"
    if not file_path.exists():
        raise FileNotFoundError(f"Locale file not found: {file_path}")
    with open(file_path, encoding="utf-8") as f:
        data: dict[str, Any] = json.load(f)
        return data


def _get_base_documents(child_number: int) -> list[str]:
    """Return list of standard document IDs needed for the application."""
    docs = ["aadhaar_mother", "bank_account", "mcp_card", "category_proof"]
    if child_number == 2:
        docs.append("birth_certificate")
    return docs


def _ineligible_result(
    reason_code: str,
    reason_key: str,
    fallback: str,
    reasons: dict[str, Any],
    scheme_version: Any,
) -> EligibilityResult:
    """Create a consistent ineligible result from localized rule data."""
    return EligibilityResult(
        eligible=False,
        benefit_amount_inr=0,
        installments=[],
        reason_code=reason_code,
        reason_hi=reasons.get(reason_key, fallback),
        required_documents=[],
        next_steps=[],
        metadata={"scheme_version": scheme_version},
    )


def _check_basic_rules(
    answers: EligibilityAnswers, reasons: dict[str, Any], scheme_version: Any
) -> EligibilityResult | None:
    """Apply pregnancy, employment, and qualifying-category rules."""
    if not answers.is_pregnant_or_lactating:
        return _ineligible_result(
            "INELIGIBLE_NOT_PREGNANT_LACTATING",
            "ineligible_not_pregnant_lactating",
            "यह योजना केवल गर्भवती महिलाओं और स्तनपान कराने वाली माताओं के लिए है।",
            reasons,
            scheme_version,
        )
    if answers.is_govt_or_psu_employee:
        return _ineligible_result(
            "INELIGIBLE_GOVT_EMPLOYEE",
            "ineligible_govt_employee",
            "सरकारी या पीएसयू कर्मचारियों को यह लाभ नहीं मिलता।",
            reasons,
            scheme_version,
        )
    if not answers.categories:
        return _ineligible_result(
            "INELIGIBLE_NO_CATEGORY",
            "ineligible_no_category",
            "कम से कम एक पात्र सामाजिक/कल्याणकारी श्रेणी होना आवश्यक है।",
            reasons,
            scheme_version,
        )
    return None


def _check_second_child_rule(
    answers: EligibilityAnswers, reasons: dict[str, Any], scheme_version: Any
) -> EligibilityResult | None:
    """Reject second-child cases where the child is not a girl."""
    if answers.child_number == 2 and not answers.second_child_is_girl:
        return _ineligible_result(
            "INELIGIBLE_SECOND_CHILD_BOY",
            "ineligible_second_child_boy",
            "दूसरी संतान के लिए लाभ केवल तभी मिलता है जब संतान कन्या हो।",
            reasons,
            scheme_version,
        )
    return None


def _benefit_details(
    answers: EligibilityAnswers, scheme: dict[str, Any], reasons: dict[str, Any]
) -> tuple[int, list[InstallmentDetail], str, str]:
    """Return the configured benefit, installments, code, and Hindi explanation."""
    is_first_child = answers.child_number == 1
    key = "first_child" if is_first_child else "second_child_girl"
    reason_key = "eligible_first_child" if is_first_child else "eligible_second_child_girl"
    reason_code = "ELIGIBLE_FIRST_CHILD" if is_first_child else "ELIGIBLE_SECOND_CHILD_GIRL"
    default_amount = 5000 if is_first_child else 6000
    fallback = (
        "बधाई हो दीदी! आप पहली संतान के लिए ₹5,000 की मातृत्व सहायता पाने की पात्र हैं।"
        if is_first_child
        else "बधाई हो दीदी! दूसरी संतान कन्या होने पर आप ₹6,000 पाने की पात्र हैं।"
    )
    config = scheme.get("benefits", {}).get(key, {})
    installments = [InstallmentDetail(**item) for item in config.get("installments", [])]
    return (
        config.get("total_amount_inr", default_amount),
        installments,
        reason_code,
        reasons.get(reason_key, fallback),
    )


def check_pmmvy_eligibility(answers: EligibilityAnswers) -> EligibilityResult:
    """Evaluate PMMVY eligibility using deterministic Python rules only."""
    scheme = load_scheme_data("pmmvy")
    locales = load_locale_data("hi")
    reasons = locales.get("reasons", {})
    scheme_version = scheme.get("version")
    rejection = _check_basic_rules(answers, reasons, scheme_version)
    if rejection is None:
        rejection = _check_second_child_rule(answers, reasons, scheme_version)
    if rejection is not None:
        return rejection

    amount, installments, reason_code, reason_hi = _benefit_details(answers, scheme, reasons)
    steps = locales.get("steps", {})
    return EligibilityResult(
        eligible=True,
        benefit_amount_inr=amount,
        installments=installments,
        reason_code=reason_code,
        reason_hi=reason_hi,
        required_documents=_get_base_documents(answers.child_number),
        next_steps=[steps.get(f"step_{number}", "") for number in range(1, 4)],
        metadata={
            "scheme_name": scheme.get("name_hi"),
            "version": scheme_version,
            "source": scheme.get("source"),
            "disclaimer": scheme.get("disclaimer_hi"),
        },
    )
