# Requirements Mapping Matrix: Sakhi – आपकी आवाज़ दीदी

This document maps every phrase from the hackathon problem statement and evaluation criteria directly to implemented features, code modules, and automated tests.

| Evaluation Signal / Problem Statement Phrase | Architectural Feature & Implementation | Source File(s) | Test Verification File(s) | CI Verification Job |
| :--- | :--- | :--- | :--- | :--- |
| **"First-time woman user"** | Welcoming female persona ("सखी दीदी"), maternal health (PMMVY 2.0) focus, village-friendly scripted Hindi | `app/services/gemini_service.py`, `app/data/locales/hi.json` | `tests/unit/test_eligibility.py`, `tests/integration/test_chat_flow.py` | `test` |
| **"No English"** | Devanagari Hindi default (`<html lang="hi">`), localized audio dialogues, Devanagari UI buttons | `app/static/index.html`, `app/data/locales/hi.json` | `tests/accessibility/test_accessibility.py` | `test` |
| **"No tech background"** | Big visual buttons (👍 हाँ / 👎 नहीं), picture cards, 5 visual progress dots (no confusing percentages) | `app/static/js/ui.js`, `app/static/css/style.css` | `tests/accessibility/test_accessibility.py` | `test` |
| **"No one to ask"** | Deterministic Hindi conversational guide and API-only scripted practice endpoint | `app/services/gemini_service.py`, `app/routes/vision.py` | `tests/integration/test_chat_flow.py`, `tests/integration/test_vision_and_practice.py` | `test` |
| **"Independently access"** | End-to-end self-service: eligibility check, document checklist, nearest Anganwadi locator, bilingual officer card | `app/services/card_service.py`, `app/services/maps_service.py` | `tests/integration/test_voice_and_tools.py` | `test` |
| **"Voice or simple text"** | 130px microphone (Cloud Speech STT), optional labeled text input, and visible choice buttons | `app/routes/voice.py`, `app/static/js/audio.js`, `app/static/js/app.js` | `tests/accessibility/test_accessibility.py`, `tests/integration/test_chat_flow.py` | `test` |
| **"Zero prior digital knowledge"** | Single-tap start, spoken button prompts, no typing required, zero hamburger menus or nested workflows | `app/static/index.html`, `app/static/js/app.js` | `tests/accessibility/test_accessibility.py` | `test` |
| **"Deterministic Rules Engine"** | LLM prohibited from deciding money/eligibility. Pure Python rules engine using PMMVY 2.0 Mission Shakti rules | `app/services/eligibility.py`, `app/data/schemes/pmmvy.json` | `tests/unit/test_eligibility.py` | `test` |
| **"Privacy & Shared Phone"** | Instant "छुपाएँ" (Escape key recipe panic screen), "सब मिटाएँ" (Firestore session wipe), and only a random session ID in `sessionStorage` | `app/static/js/privacy.js`, `app/routes/tools.py`, `app/services/session_service.py` | `tests/integration/test_voice_and_tools.py` | `test` |
| **"Zero PII Logging"** | Structured JSON stdout logger emits static event details and does not include request content | `app/core/logging.py` | `tests/unit/test_services_edge_cases.py` | `security`, `test` |
| **"Location Privacy"** | Coordinate rounding to 2 decimal places (~1.1 km precision) before Places API search | `app/services/maps_service.py` | `tests/integration/test_voice_and_tools.py` | `test` |
| **"Graceful Fallbacks"** | Gemini, STT, TTS, Places, Firestore failures have local fallbacks | `app/services/*.py`, `app/core/config.py` | `tests/unit/test_mocked_services.py`, `tests/unit/test_services_edge_cases.py` | `test`, `docker` |
| **"Code Quality & Testing"** | Strict type hints, docstrings, Ruff, strict mypy, and ≥90% pytest coverage | `pyproject.toml`, `.github/workflows/ci.yml` | `tests/test_repo_config.py` | `lint`, `test` |
| **"SDG Alignment (5, 4, 10)"** | Direct financial empowerment for mothers, digital literacy education through voice, civic inclusion | `app/data/schemes/pmmvy.json`, `README.md` | `tests/unit/test_eligibility.py` | `test` |
