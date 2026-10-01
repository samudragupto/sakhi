"""Officer card generator creating bilingual card representations and QR code."""

import base64
import io
from typing import Any

import qrcode

from app.models.card import OfficerCardData, OfficerCardRequest
from app.services.eligibility import load_scheme_data


def _create_qr_code(official_url: str) -> str:
    """Generate a data URL for the official PMMVY portal QR code."""
    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_M,
        box_size=8,
        border=2,
    )
    qr.add_data(official_url)
    qr.make(fit=True)
    image = qr.make_image(fill_color="black", back_color="white")
    buffer = io.BytesIO()
    image.save(buffer, format="PNG")
    encoded = base64.b64encode(buffer.getvalue()).decode("utf-8")
    return f"data:image/png;base64,{encoded}"


def _get_document_labels(
    scheme: dict[str, Any], requested_ids: list[str]
) -> tuple[list[str], list[str]]:
    """Resolve Hindi and English display labels for requested scheme documents."""
    document_map = {
        item["id"]: (item["name_hi"], item.get("name_en", item["name_hi"]))
        for item in scheme.get("required_documents", [])
    }
    labels = [document_map.get(item, (item, item)) for item in requested_ids]
    return [item[0] for item in labels], [item[1] for item in labels]


def generate_officer_card(req: OfficerCardRequest) -> OfficerCardData:
    """Generate bilingual card and official portal QR code base64."""
    scheme = load_scheme_data("pmmvy")

    official_url = scheme.get("where_to_apply", {}).get("online_portal", "https://pmmvy.wcd.gov.in")

    benefit_hi = f"₹{req.benefit_amount_inr:,} (मातृ वंदना सहायता)"
    benefit_en = f"₹{req.benefit_amount_inr:,} (Maternity Benefit Assistance)"
    docs_hi, docs_en = _get_document_labels(scheme, req.required_documents)

    return OfficerCardData(
        title_hi="प्रधानमंत्री मातृ वंदना योजना (PMMVY) - नागरिक पात्रता कार्ड",
        title_en="Pradhan Mantri Matru Vandana Yojana - Citizen Eligibility Card",
        benefit_hi=benefit_hi,
        benefit_en=benefit_en,
        documents_hi=docs_hi,
        documents_en=docs_en,
        qr_code_base64=_create_qr_code(official_url),
        official_portal_url=official_url,
        disclaimer_hi=scheme.get("disclaimer_hi", "अंतिम पुष्टि अपनी आंगनवाड़ी में करें।"),
    )
