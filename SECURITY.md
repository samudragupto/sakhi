# Security Policy & Threat Model: Sakhi (सखी)

## 1. Overview
Sakhi is designed as a **privacy-first, zero-PII civic-tech application** serving rural citizens, primarily women, often using **shared family or community mobile devices**. Because users may not own their devices, traditional session caching and client-side history present acute domestic privacy and safety risks.

## 2. Threat Model & Mitigations

### Threat 1: Shared Phone Snooping & Domestic Privacy
- **Risk:** Family members or third parties accessing browsing history, pregnancy records, or welfare benefit inquiries on a shared handset.
- **Mitigation:**
  - **Tab-Scoped Session:** Answers are not stored in browser storage; `sessionStorage` holds only a random session identifier.
  - **Panic Button ("छुपाएँ"):** Persistent floating button, keyboard shortcut (`Escape`), and mobile triple-tap gesture instantly swap the entire viewport to an innocuous cooking recipe ("स्वादिष्ट तड़का दाल") and immediately terminate all audio output.
  - **Instant Data Erasure ("सब मिटाएँ"):** A single tap fires `DELETE /api/v1/session`, purging all in-memory or Firestore anonymous session state and resetting the UI.

### Threat 2: Personally Identifiable Information (PII) Leakage
- **Risk:** Aadhaar numbers, phone numbers, full names, or audio recordings leaking into logs, analytics, or persistent databases.
- **Mitigation:**
  - **Deterministic Anonymity:** Sessions are identified by cryptographically random browser-generated identifiers.
  - **Allowlisted Log Formatter:** `app/core/logging.py` omits free-text messages, exception details, and session IDs; it emits only event, severity, timestamp, latency, and status fields.
  - **No Local Media Persistence:** Audio and uploaded images are processed in memory and are not written to local storage. When configured, audio and document images are sent to Google APIs for inference.

### Threat 3: Location Privacy
- **Risk:** Exact GPS coordinates revealing an individual's home or shelter.
- **Mitigation:**
  - `app/services/maps_service.py` applies `round_coordinates()` to round latitude and longitude to 2 decimal places (~1.1 km precision) before any external API queries. Raw coordinates are never stored or logged.

### Threat 4: Prompt Injection & Jailbreaks
- **Risk:** Malicious inputs attempting to change Sakhi's persona, extract internal prompts, or output harmful medical advice.
- **Mitigation:**
  - **Deterministic Python Enforcement:** Gemini is not used in the eligibility conversation. Eligibility and benefit amounts are calculated only by Python code in `app/services/eligibility.py`.

### Threat 5: Injection & Denial of Service (DoS)
- **Risk:** Overly large audio/image uploads, script injection, or API flooding.
- **Mitigation:**
  - `slowapi` enforces strict rate limits (20 req/min for chat/voice, 5 req/min for vision).
  - Strict Content-Security-Policy (CSP) with `default-src 'self'` and no inline scripts.
  - Strict payload bounds: Audio ≤ 1 MB, Images ≤ 5 MB, text inputs truncated to 500 characters.

## 3. Data Retention & Firestore TTL
- Anonymous session documents in Cloud Firestore expire automatically via Time-To-Live (TTL):
  ```bash
  gcloud firestore fields ttls update expire_at \
      --collection-group=sessions \
      --enable-ttl \
      --project="$GCP_PROJECT_ID"
  ```
- All temporary session records are expunged within 24 hours.

## 4. Vulnerability Reporting
If you discover a potential security vulnerability, please report it privately to the maintainers rather than opening a public issue.
