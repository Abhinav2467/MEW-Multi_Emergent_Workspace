# Project MEW Autofill Backend & Verification Suite — Design Document

**Date:** 2026-07-28  
**Author:** AI Pair Programmer & Lead Developer  
**Status:** Approved  

---

## 1. Overview & Objectives

Project MEW (Multimodal Emergent Workspace) requires a high-performance, secure backend to support the Chrome Extension Autofill workflow. This document specifies the complete backend architecture, security controls, autofill payload APIs, AI fuzzy-matching fallbacks, and the integrated testing suite.

### Key Objectives
1. **Security & Anti-Detection:** Provide secure, authenticated API access (`X-MEW-Api-Key`), strict CORS boundaries for extension origins, rate limiting, and clean headers.
2. **Payload Delivery & AI Fallback:** Deliver pre-normalized candidate profile data for low-latency local extension matching, with a `gemini-1.5-flash` endpoint for ambiguous/custom form fields.
3. **Integrated Test Suite:** Provide a locally served `/test-forms` suite with diverse real-world form patterns (Standard, React controlled inputs, Multi-step wizard, Shadow DOM, Custom QA) and live synthetic event logging.

---

## 2. System Architecture & Directory Layout

The backend is built as a modular FastAPI micro-service inside `development/mew/backend`.

```text
development/mew/
├── backend/
│   ├── main.py                     # FastAPI application entrypoint & middleware configuration
│   ├── config.py                   # Environment variables, settings, and API key management
│   ├── security/
│   │   ├── __init__.py
│   │   ├── auth.py                 # API key validation middleware & secret generation
│   │   └── rate_limiter.py         # Token-bucket rate limiter (60 req/min)
│   ├── schemas/
│   │   ├── __init__.py
│   │   ├── profile.py              # Candidate profile Pydantic models
│   │   └── autofill.py             # Autofill payload, DOM field descriptor, and match response models
│   ├── agents/
│   │   ├── __init__.py
│   │   └── autofill_agent.py       # LangChain + Gemini 1.5 Flash fuzzy field matcher
│   ├── routes/
│   │   ├── __init__.py
│   │   ├── autofill.py             # /api/v1/autofill-payload & /api/v1/autofill-payload/match
│   │   ├── profile.py              # /api/v1/profile (GET & PUT)
│   │   └── testing.py              # /test-forms (HTML test suite) & /autofill/preview
│   ├── data/
│   │   └── profile.json            # Persistent candidate profile storage
│   ├── static/
│   │   └── test_forms.html         # Interactive test forms page with synthetic event logging
│   └── tests/
│       ├── test_auth.py            # Security & API key unit tests
│       └── test_autofill.py        # Payload & fuzzy matching integration tests
└── requirements.txt                # Dependencies (fastapi, uvicorn, pydantic, langchain-google-genai, etc.)
```

---

## 3. Security & Anti-Detection Architecture

### 3.1 Authentication (`X-MEW-Api-Key`)
* **Header Requirement:** All API endpoints under `/api/v1/*` require `X-MEW-Api-Key: <32_char_hex_key>`.
* **Automatic Provisioning:** On server startup, `config.py` checks for `MEW_API_KEY` in `.env`. If missing, it generates a cryptographically secure 32-character hex key (`mew_sk_...`), persists it in `.env`, and logs it cleanly to stdout.
* **Unauthorized Access:** Requests with missing or invalid keys return `HTTP 401 Unauthorized`.

### 3.2 CORS & Origin Constraints
* **Allowed Origins:** `chrome-extension://*`, `http://localhost:*`, `http://127.0.0.1:*`.
* **Security Headers:** Adds `X-Content-Type-Options: nosniff` and disables unnecessary server signature headers to maintain clean local traffic.

### 3.3 Rate Limiting
* **Threshold:** 60 requests per minute per API key using in-memory token bucket tracking.
* **Exceeded Response:** `HTTP 429 Too Many Requests`.

---

## 4. API Endpoints & Payload Schemas

### 4.1 `GET /api/v1/autofill-payload`
Returns pre-normalized user profile data structured for fast local client matching.

* **Response Schema (`AutofillPayloadResponse`):**
  ```json
  {
    "status": "success",
    "data": {
      "personal": {
        "first_name": "Jane",
        "last_name": "Doe",
        "full_name": "Jane Doe",
        "email": "jane.doe@example.com",
        "phone": "+15550199823",
        "linkedin_url": "https://linkedin.com/in/janedoe",
        "github_url": "https://github.com/janedoe",
        "portfolio_url": "https://janedoe.dev",
        "location": "San Francisco, CA",
        "work_authorization": "US Citizen"
      },
      "professional": {
        "current_title": "Senior Software Engineer",
        "years_experience": 6,
        "primary_skills": ["Python", "FastAPI", "React", "TypeScript", "LangChain"],
        "summary": "Experienced software engineer specializing in backend systems..."
      },
      "custom_qa": {
        "willing_to_relocate": "Yes",
        "notice_period": "2 weeks",
        "desired_salary": "$150,000"
      },
      "event_hints": {
        "dispatch_sequence": ["focus", "input", "change", "blur"],
        "simulate_synthetic_events": true
      }
    }
  }
  ```

### 4.2 `POST /api/v1/autofill-payload/match`
AI-assisted fallback endpoint for unlabelled or complex DOM elements using `gemini-1.5-flash` with structured outputs (`ChatGoogleGenerativeAI.with_structured_output`).

* **Request Body (`FuzzyMatchRequest`):**
  ```json
  {
    "fields": [
      {
        "element_id": "custom-qa-4",
        "label": "Total years of Python experience?",
        "placeholder": "e.g., 5",
        "tag_name": "input",
        "input_type": "number"
      }
    ]
  }
  ```
* **Response Body (`FuzzyMatchResponse`):**
  ```json
  {
    "matches": [
      {
        "element_id": "custom-qa-4",
        "matched_key": "professional.years_experience",
        "value": "6",
        "confidence": 0.95,
        "reasoning": "Label explicitly requests years of Python experience, matching profile's 6 years."
      }
    ]
  }
  ```

### 4.3 Profile Management & Resume JSON Synchronization
* **`GET /api/v1/profile`**: Returns current candidate profile JSON.
* **`PUT /api/v1/profile`**: Accepts structured JSON (e.g. from the Resume Parser Agent, manual edits, or external uploads) and updates the active profile in `backend/data/profile.json`.
* **Automatic Downstream Synchronization:** Whenever `backend/data/profile.json` is updated with new parsed resume JSON, `GET /api/v1/autofill-payload` and `POST /api/v1/autofill-payload/match` immediately reflect the updated details across all extension queries without requiring server restarts or code edits.

---

## 5. Integrated Testing Suite (`/test-forms`)

The backend serves a dedicated interactive HTML test runner at `http://localhost:8000/test-forms` for testing Chrome Extension autofill behavior.

### 5.1 Test Scenarios Included
1. **Scenario 1: Standard Job Application Form** (Standard inputs, standard autocomplete attributes).
2. **Scenario 2: Framework/React Controlled Inputs** (State-bound inputs that require `input`, `change`, and `blur` events to update internal React state).
3. **Scenario 3: Custom QA & Ambiguous Fields** (Unlabelled inputs, custom questions requiring AI fuzzy matching).
4. **Scenario 4: Multi-Step Application Wizard** (Step 1: Contact -> Step 2: Experience -> Step 3: Review).
5. **Scenario 5: Shadow DOM Encapsulated Form** (Fields contained within a Web Component Shadow Root).

### 5.2 Live Synthetic Event Log Component
The test page includes an interactive event monitor at the bottom of the page. When the Chrome Extension injects values into form inputs, the page visually logs all received JavaScript events (`focus`, `input`, `change`, `blur`) to confirm framework compatibility.

---

## 6. Verification Plan

### 6.1 Automated Tests
* Run `pytest backend/tests/test_auth.py` to verify API key validation, 401 errors, and CORS header rules.
* Run `pytest backend/tests/test_autofill.py` to verify payload schema responses, profile persistence, and AI fuzzy field matching logic.

### 6.2 Manual Verification
* Start server via `uvicorn backend.main:app --reload`.
* Access `http://localhost:8000/test-forms` in Chrome.
* Open Developer Tools and verify API Key header authentication and payload fetching.
* Trigger autofill using your Chrome Extension content script against Scenarios 1–5 and observe the live Event Log.

---

## 7. Spec Self-Review Summary

- **Placeholder scan:** No placeholders, TBDs, or vague items remaining.
- **Internal consistency:** File layout, schemas, security headers, and test routes match across all sections.
- **Scope check:** Strictly focused on backend design, security, autofill payload generation, AI fallback matcher, and test suite.
- **Ambiguity check:** Schema models, CORS origins, and API key handling are explicitly defined.
