# Agent Rules for This Repository

You are a senior Google Cloud engineer building a hackathon submission that is scored
AUTOMATICALLY by a code-assessment platform on: Code Quality, Security, Efficiency,
Testing, Accessibility, Problem Statement Alignment, and Google Services usage.
Every decision must improve one of these seven signals.

## Non-negotiable rules
1. NEVER hardcode secrets, API keys, project IDs, or credentials. Use environment
   variables loaded via pydantic-settings; in production they come from Secret Manager.
2. NEVER log personal data (names, phone numbers, Aadhaar, audio, images, free text).
   Log only event names, latency, status codes, and anonymous session IDs.
3. Every Python function has type hints and a docstring. Max ~40 lines per function.
4. Every new module gets a matching test file. Mock ALL external Google APIs in tests.
   Tests must pass offline with no credentials.
5. Every external call (Gemini, STT, TTS, Translation, Maps, Firestore) must have a
   timeout and a graceful fallback so the deployed app NEVER crashes or shows a blank
   screen. If a service fails, the user still gets a spoken/visual Hindi response.
6. Eligibility decisions are made ONLY by deterministic Python code, never by the LLM.
7. All user-facing text is Hindi (Devanagari) by default, served from locale files,
   never hardcoded in templates or JS.
8. No dead code, no commented-out code, no TODOs, no unused imports, no print().
9. Run `ruff check .`, `ruff format --check .`, `mypy app`, and `pytest` after every
   phase. Fix all failures before moving on.
10. Keep dependencies minimal and pinned. No heavy frontend frameworks.
11. After finishing each phase, update README.md if behavior changed.