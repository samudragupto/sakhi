"""Data models for Vision (Paper Whisperer) and Practice Mode."""

from pydantic import BaseModel, Field


class DocumentExplainResponse(BaseModel):
    """Structured explanation of an uploaded government letter or form."""

    summary_hi: str = Field(..., description="Simple 3-4 sentence Hindi spoken summary")
    what_to_do_hi: str = Field(..., description="Action required by applicant in Hindi")


class PracticeRequest(BaseModel):
    """Input query for Anganwadi rehearsal role-play."""

    user_utterance: str = Field(
        ..., max_length=500, description="What the woman wants to say to the officer"
    )


class PracticeResponse(BaseModel):
    """Role-play feedback and encouraging coaching."""

    officer_reply_hi: str = Field(..., description="Polite response from Anganwadi Didi")
    coaching_tip_hi: str = Field(..., description="Encouraging advice for visiting the centre")
