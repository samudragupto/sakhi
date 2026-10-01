"""Gemini document summaries and deterministic PMMVY chat flow."""

import asyncio
from typing import Any

from app.core.config import get_settings
from app.core.logging import logger
from app.models.chat import ChatResponse, QuickReply, UIAction
from app.models.eligibility import EligibilityAnswers, EligibilityCategory
from app.models.session import SessionDoc
from app.models.vision import DocumentExplainResponse
from app.services.eligibility import check_pmmvy_eligibility, load_locale_data

DOCUMENT_PROMPT = """इस दस्तावेज़ में दिखाई देने वाली जानकारी का सरल हिंदी में सार दें।
अस्पष्ट पाठ का अनुमान न लगाएँ। पात्रता या लाभ की राशि तय न करें।"""


def _result_response(answers: EligibilityAnswers) -> ChatResponse:
    """Evaluate answers deterministically and create the corresponding chat response."""
    result = check_pmmvy_eligibility(answers)
    return ChatResponse(
        speech_text=result.reason_hi,
        caption=result.reason_hi,
        ui_action=UIAction.SHOW_RESULT,
        data=result.model_dump(),
    )


def _category_replies() -> list[QuickReply]:
    """Return deterministic welfare-category choices in Hindi."""
    return [
        QuickReply(label_hi="बीपीएल/राशन कार्ड", value="BPL_RATION_CARD"),
        QuickReply(label_hi="ई-श्रम कार्ड", value="E_SHRAM"),
        QuickReply(label_hi="मनरेगा जॉब कार्ड", value="MGNREGA"),
        QuickReply(label_hi="SC/ST श्रेणी", value="SC_ST"),
        QuickReply(label_hi="कोई कार्ड नहीं", value="NONE"),
    ]


def _ask_category() -> ChatResponse:
    """Ask the user to choose a qualifying welfare category."""
    return ChatResponse(
        speech_text="क्या आपके पास राशन कार्ड, ई-श्रम, मनरेगा, या किसान सम्मान निधि जैसी कोई पात्रता है?",
        caption="क्या आपके पास राशन कार्ड, ई-श्रम, या अन्य कार्ड है?",
        ui_action=UIAction.ASK_CHOICE,
        quick_replies=_category_replies(),
    )


def _handle_step_one(message: str, lower: str, session: SessionDoc) -> ChatResponse:
    """Handle the pregnancy or lactation question."""
    if any(term in message for term in ("हाँ", "गर्भवती", "बच्चा")) or "yes" in lower:
        session.answers["is_pregnant_or_lactating"] = True
        session.step = 2
        return ChatResponse(
            speech_text="यह आपकी कौन सी संतान है दीदी? पहली संतान है या दूसरी?",
            caption="यह आपकी कौन सी संतान है? पहली या दूसरी?",
            ui_action=UIAction.ASK_CHOICE,
            quick_replies=[
                QuickReply(label_hi="पहली संतान", value="1"),
                QuickReply(label_hi="दूसरी संतान", value="2"),
            ],
        )
    if "नहीं" in message or "no" in lower:
        session.answers["is_pregnant_or_lactating"] = False
        return _result_response(
            EligibilityAnswers(
                is_pregnant_or_lactating=False,
                child_number=1,
                categories=[EligibilityCategory.BPL_RATION_CARD],
                is_govt_or_psu_employee=False,
            )
        )
    return ChatResponse(
        speech_text="नमस्ते दीदी! क्या आप अभी गर्भवती हैं या आपका हाल ही में बच्चा हुआ है?",
        caption="क्या आप अभी गर्भवती हैं या हाल ही में बच्चा हुआ है?",
        ui_action=UIAction.ASK_YES_NO,
        quick_replies=[
            QuickReply(label_hi="👍 हाँ", value="हाँ"),
            QuickReply(label_hi="👎 नहीं", value="नहीं"),
        ],
    )


def _handle_step_two(message: str, session: SessionDoc) -> ChatResponse:
    """Handle first- or second-child selection."""
    if any(term in message for term in ("1", "एक", "पहला", "पहली")):
        session.answers["child_number"] = 1
        session.answers["second_child_is_girl"] = None
        session.step = 4
        return _ask_category()
    if any(term in message for term in ("2", "दो", "दूसरा", "दूसरी")):
        session.answers["child_number"] = 2
        session.step = 3
        return ChatResponse(
            speech_text="क्या आपकी दूसरी संतान कन्या (बेटी) है?",
            caption="क्या आपकी दूसरी संतान कन्या (बेटी) है?",
            ui_action=UIAction.ASK_YES_NO,
            quick_replies=[
                QuickReply(label_hi="👍 हाँ, बेटी है", value="हाँ"),
                QuickReply(label_hi="👎 नहीं, बेटा है", value="नहीं"),
            ],
        )
    return ChatResponse(
        speech_text="कृपया बताएं कि यह आपकी पहली संतान है या दूसरी?",
        caption="पहली संतान या दूसरी संतान?",
        ui_action=UIAction.ASK_CHOICE,
        quick_replies=[
            QuickReply(label_hi="पहली", value="1"),
            QuickReply(label_hi="दूसरी", value="2"),
        ],
    )


def _handle_step_three(message: str, lower: str, session: SessionDoc) -> ChatResponse:
    """Handle the second-child girl-child rule."""
    is_girl = any(term in message for term in ("हाँ", "बेटी", "कन्या")) or "yes" in lower
    session.answers["second_child_is_girl"] = is_girl
    if not is_girl:
        return _result_response(
            EligibilityAnswers(
                is_pregnant_or_lactating=True,
                child_number=2,
                second_child_is_girl=False,
                categories=[EligibilityCategory.BPL_RATION_CARD],
                is_govt_or_psu_employee=False,
            )
        )
    session.step = 4
    return _ask_category()


def _category_for_message(message: str, lower: str) -> list[EligibilityCategory]:
    """Map recognized welfare terms to the deterministic eligibility enum."""
    category_terms = {
        "bpl": EligibilityCategory.BPL_RATION_CARD,
        "ration": EligibilityCategory.BPL_RATION_CARD,
        "राशन": EligibilityCategory.BPL_RATION_CARD,
        "e_shram": EligibilityCategory.E_SHRAM,
        "ई-श्रम": EligibilityCategory.E_SHRAM,
        "mgnrega": EligibilityCategory.MGNREGA,
        "मनरेगा": EligibilityCategory.MGNREGA,
        "sc_st": EligibilityCategory.SC_ST,
        "जाति": EligibilityCategory.SC_ST,
        "किसान": EligibilityCategory.PM_KISAN,
        "pm_kisan": EligibilityCategory.PM_KISAN,
        "आय": EligibilityCategory.INCOME_BELOW_8_LAKH,
        "आशा": EligibilityCategory.AWW_AWH_ASHA,
    }
    for term, category in category_terms.items():
        if term in lower or term in message:
            return [category]
    return [] if "none" in lower or "नहीं" in message else [EligibilityCategory.BPL_RATION_CARD]


def _handle_step_four(message: str, session: SessionDoc) -> ChatResponse:
    """Store the category choice and ask about government employment."""
    session.answers["categories"] = _category_for_message(message, message.lower())
    session.step = 5
    return ChatResponse(
        speech_text="क्या आप या आपके पति किसी नियमित सरकारी या पीएसयू नौकरी में हैं?",
        caption="क्या आप या आपके पति नियमित सरकारी नौकरी में हैं?",
        ui_action=UIAction.ASK_YES_NO,
        quick_replies=[
            QuickReply(label_hi="👍 हाँ, सरकारी नौकरी है", value="हाँ"),
            QuickReply(label_hi="👎 नहीं, नहीं है", value="नहीं"),
        ],
    )


def _handle_step_five(message: str, lower: str, session: SessionDoc) -> ChatResponse:
    """Evaluate final answers using Python eligibility rules."""
    is_govt = any(term in message for term in ("हाँ", "सरकारी")) or "yes" in lower
    session.answers["is_govt_or_psu_employee"] = is_govt
    return _result_response(
        EligibilityAnswers(
            is_pregnant_or_lactating=session.answers.get("is_pregnant_or_lactating", True),
            child_number=session.answers.get("child_number", 1),
            second_child_is_girl=session.answers.get("second_child_is_girl"),
            categories=session.answers.get("categories", [EligibilityCategory.BPL_RATION_CARD]),
            is_govt_or_psu_employee=is_govt,
        )
    )


def _run_scripted_fallback_flow(user_msg: str, session: SessionDoc) -> ChatResponse:
    """Route each question step to its deterministic handler."""
    lower = user_msg.strip().lower()
    if session.step == 1:
        return _handle_step_one(user_msg, lower, session)
    if session.step == 2:
        return _handle_step_two(user_msg, session)
    if session.step == 3:
        return _handle_step_three(user_msg, lower, session)
    if session.step == 4:
        return _handle_step_four(user_msg, session)
    return _handle_step_five(user_msg, lower, session)


async def process_chat(message: str, session: SessionDoc) -> ChatResponse:
    """Process chat with deterministic rules and scripted Hindi prompts only."""
    return _run_scripted_fallback_flow(message, session)


def _document_fallback() -> DocumentExplainResponse:
    """Return generic localized guidance when document analysis is unavailable."""
    help_text = load_locale_data("hi").get("document_help", {})
    return DocumentExplainResponse(
        summary_hi=help_text.get("summary", "फोटो अभी पढ़ी नहीं जा सकी।"),
        what_to_do_hi=help_text.get("next_step", "कृपया साफ़ फोटो लेकर आंगनवाड़ी में दिखाएँ।"),
    )


async def explain_document_image(image_bytes: bytes, content_type: str) -> DocumentExplainResponse:
    """Summarize a document image with Gemini or return generic Hindi guidance."""
    settings = get_settings()
    if not settings.gemini_api_key:
        return _document_fallback()

    try:
        from google import genai
        from google.genai import types

        client = genai.Client(
            api_key=settings.gemini_api_key,
            http_options=types.HttpOptions(timeout=5000),
        )
        image_part = types.Part.from_bytes(data=image_bytes, mime_type=content_type)
        image_contents: Any = [DOCUMENT_PROMPT, image_part]
        response = await asyncio.to_thread(
            client.models.generate_content,
            model=settings.gemini_model,
            contents=image_contents,
            config=types.GenerateContentConfig(temperature=0.1, max_output_tokens=300),
        )
        if response and response.text and response.text.strip():
            guidance = load_locale_data("hi").get("document_help", {})
            return DocumentExplainResponse(
                summary_hi=response.text.strip(),
                what_to_do_hi=guidance.get("next_step", "कृपया जानकारी की पुष्टि आंगनवाड़ी में करें।"),
            )
    except Exception:
        logger.warning(
            "Gemini document summary failed, returning localized guidance",
            extra={"event": "gemini_document_fallback"},
        )

    return _document_fallback()
