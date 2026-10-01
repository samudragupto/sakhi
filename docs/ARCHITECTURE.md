# System Architecture: Sakhi – आपकी आवाज़ दीदी

## 1. High-Level System Architecture

```mermaid
graph TD
    subgraph ClientLayer["Zero-Literacy Frontend (< 50 KB Vanilla JS)"]
        User(["Rural Woman User / Shared Mobile"]) <-->|Devanagari Voice / Audio Playback| AudioEngine["Audio Pipeline (WebM Mic Capture & TTS Playback)"]
        User <-->|Big Touch Cards / Yes-No Buttons| DOM["Accessible Semantic DOM (WCAG 2.2 AA)"]
        DOM -->|Escape / Triple-Tap| PanicScreen["Neutral Panic Recipe Screen (छुपाएँ)"]
    end

    subgraph Gateway["FastAPI Async Gateway (Port 8080)"]
        AudioEngine -->|POST /api/v1/voice/transcribe| VoiceRouter["Voice Router (/voice)"]
        AudioEngine <--|POST /api/v1/voice/speak| VoiceRouter
        DOM -->|POST /api/v1/chat| ChatRouter["Chat Router (/chat)"]
        DOM -->|POST /api/v1/vision/explain| VisionRouter["Document Summary Router (/vision)"]
        DOM -->|GET /api/v1/places/nearby| PlacesRouter["Places Router (/places)"]
        DOM -->|POST /api/v1/card| CardRouter["Card Router (/card)"]
        DOM -->|DELETE /api/v1/session| SessionRouter["Session Router (/session)"]
        
        SecMiddleware["Security Headers (Strict CSP, Nosniff, HSTS)"] --> Gateway
        RateLimiter["slowapi Rate Limiter (20/min voice & chat)"] --> Gateway
        LogFilter["Structured JSON stdout logger"] --> Gateway
    end

    subgraph CoreEngines["Deterministic Core Engines & Data"]
        ChatRouter --> EligibilityEngine["PMMVY 2.0 Rules Engine (Pure Python)"]
        EligibilityEngine --- SchemeJSON[("pmmvy.json (Single Source of Truth)")]
        EligibilityEngine --- LocaleJSON[("hi.json")]
    end

    subgraph GoogleServices["Google Cloud Platform Services & Fallbacks"]
        VisionRouter -->|google-genai| GeminiModel["Gemini 2.5 Flash image summary"]
        GeminiModel -. Fallback .-> VisionRouter
        
        VoiceRouter <-->|gRPC / REST| CloudSTT["Cloud Speech-to-Text (hi-IN)"]
        VoiceRouter <-->|gRPC / REST| CloudTTS["Cloud Text-to-Speech (hi-IN-Neural2-A)"]
        CloudTTS --- LRUCache[("In-Memory LRU Audio Cache")]
        
        PlacesRouter <-->|httpx async| PlacesAPI["Maps Places API (New)"]
        SessionRouter <-->|Firestore Client| FirestoreTTL[("Cloud Firestore (24h TTL)")]
    end
```

## 2. Conversational State Machine

```mermaid
stateDiagram-v2
    [*] --> Greeting : User Taps "शुरू करें"
    Greeting --> Step1_PregnancyCheck : Spoken Greeting & Question
    Step1_PregnancyCheck --> Ineligible_NotPregnant : "नहीं" (Not expecting)
    Step1_PregnancyCheck --> Step2_ChildIndex : "हाँ" (Pregnant/Lactating)
    
    Step2_ChildIndex --> Step3_GirlCheck : Second Child ("2")
    Step2_ChildIndex --> Step4_CategoryCheck : First Child ("1")
    
    Step3_GirlCheck --> Ineligible_BoyChild : "नहीं, बेटा है"
    Step3_GirlCheck --> Step4_CategoryCheck : "हाँ, बेटी है"
    
    Step4_CategoryCheck --> Ineligible_NoCategory : "कोई कार्ड नहीं है"
    Step4_CategoryCheck --> Step5_GovtExclusion : Ration / e-Shram / SC-ST / etc.
    
    Step5_GovtExclusion --> Ineligible_GovtEmployee : "हाँ, सरकारी नौकरी है"
    Step5_GovtExclusion --> EligibleResult : "नहीं, कोई नौकरी नहीं है"
    
    EligibleResult --> OfficerCardView : User taps "अधिकारी को दिखाएँ"
    EligibleResult --> AnganwadiFinder : User taps "आंगनवाड़ी खोजें"
    
    Ineligible_NotPregnant --> [*]
    Ineligible_BoyChild --> [*]
    Ineligible_GovtEmployee --> [*]
    Ineligible_NoCategory --> [*]
    OfficerCardView --> [*]
```

## 3. Privacy & Shared Phone Lifecycle

```mermaid
sequenceDiagram
    autonumber
    actor Woman as Rural Woman User
    participant Frontend as Mobile Browser UI
    participant Backend as FastAPI Gateway
    participant Session as Cloud Firestore (or Local Cache)

    Woman->>Frontend: Taps "शुरू करें" (Audio plays in Hindi)
    Frontend->>Backend: POST /api/v1/chat (session_id=UUID4)
    Backend->>Session: Store anonymous answers (expire_at=NOW+24h)
    Backend-->>Frontend: Spoken reply & Big Touch Cards

    Note over Woman,Frontend: Someone approaches the shared phone!
    Woman->>Frontend: Taps "छुपाएँ" OR presses Escape OR triple-taps
    Frontend->>Frontend: Instantly stop audio & swap DOM to Dal Tadka recipe
    
    Note over Woman,Frontend: Threat passes, user is finished
    Woman->>Frontend: Taps "सब मिटाएँ" (Wipe All)
    Frontend->>Backend: DELETE /api/v1/session?session_id=UUID4
    Backend->>Session: Delete session document
    Frontend->>Frontend: Clear sessionStorage & reset UI completely
```
