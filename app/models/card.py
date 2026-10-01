"""Data models for Anganwadi Officer Card."""

from pydantic import BaseModel, Field


class OfficerCardRequest(BaseModel):
    """Input payload to create an officer card."""

    child_number: int = Field(..., ge=1, le=2)
    benefit_amount_inr: int
    categories: list[str] = Field(default_factory=list)
    required_documents: list[str] = Field(default_factory=list)


class OfficerCardData(BaseModel):
    """Bilingual card presentation data and official QR code."""

    title_hi: str
    title_en: str
    benefit_hi: str
    benefit_en: str
    documents_hi: list[str]
    documents_en: list[str]
    qr_code_base64: str
    official_portal_url: str
    disclaimer_hi: str
