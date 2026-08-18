# Google OAuth Auto-Redirect, PostMessage Bridge & Universal Auth Resolution

## Overview
Transform the Google OAuth flow from a manual copy-paste experience into a seamless, modern, automated authentication experience with instant parent-tab synchronization (`postMessage`), direct auto-redirects, one-click bridge UI, and a universal input parser that handles JWT tokens, raw JSON responses, authorization codes, and callback URLs.

## Problem Description
1. When Google OAuth redirects to `/auth/callback`, the backend currently returns a raw JSON payload in the browser window (`{"access_token": "eyJ...", "user": ...}`).
2. Users copy the JWT access token and paste it into the "PASTE PRIVATE ACCESS KEY" box, which expects a Google authorization code, resulting in an `OAuth exchange failed: 400 Bad Request` error.
3. The popup/tab does not automatically notify the parent app window or redirect back to the frontend.

## Proposed Changes

### Backend

#### [MODIFY] [backend/api/routes/auth.py](file:///Users/abhi_2467/aura_folder✨/job_applying_agent/backend/api/routes/auth.py)
- In `GET /auth/callback`:
  - Check request headers (`Accept`) and query parameters (`format`, `return_url`, `state`).
  - If requested from a browser (`text/html`), return an interactive `HTMLResponse` containing:
    - `window.opener.postMessage({ type: 'MEW_GOOGLE_AUTH_SUCCESS', token, user }, '*')` for instant parent window auto-login and tab auto-close.
    - Automatic `window.location.replace(return_url + '#token=' + token)` fallback if opened in the same tab.
    - A polished, branded UI displaying candidate name, connected email, a prominent "Copy Access Token" one-click button, and a "Return to MEW Workspace" button.
  - If requested via API (`application/json`), return the existing `TokenResponse` model.
- In `GET /auth/google`:
  - Accept `return_url` / `state` parameter to pass frontend URL through Google's OAuth state.

---

### Frontend

#### [MODIFY] [claude_frontend/landing.html/index.html](file:///Users/abhi_2467/aura_folder✨/job_applying_agent/claude_frontend/landing.html/index.html)
- **Message Listener (`postMessage`)**:
  - Add global message listener for `MEW_GOOGLE_AUTH_SUCCESS` events from the Google OAuth popup.
  - Instantly store `mew_jwt_token`, set `MewApiClient.token`, sync user profile (`email`, `name`), update UI, and navigate to the next step.
- **Hash / Query Token Ingestion**:
  - Detect `#token=eyJ...` or `?token=eyJ...` on page load to automatically log in direct redirect users.
- **Universal Input Handler (`handleKeyLoginSubmit`)**:
  - If user pastes a JWT token (`eyJ...` or `Bearer eyJ...`), validate directly with `/auth/me` and authenticate.
  - If user pastes raw JSON (`{"access_token": "ey...", ...}`), parse and authenticate.
  - If user pastes a Google auth code (`4/0A...`), exchange via `/auth/callback?code=...`.
  - If user pastes a full redirect URL, extract code/token and authenticate.
- **Enhanced OAuth Window Launcher (`openGoogleAuthWindow`)**:
  - Pass `state` with current `window.location.origin` and `return_url` so the backend knows where to redirect.

---

### Automated Tests

#### [MODIFY] [backend/tests/test_email_endpoints.py](file:///Users/abhi_2467/aura_folder✨/job_applying_agent/backend/tests/test_email_endpoints.py)
- Test `/auth/callback` with `Accept: application/json` returning `TokenResponse`.
- Test `/auth/callback` with `Accept: text/html` returning HTML bridge with `postMessage` script.
- Verify existing 30 tests continue to pass 100%.

## Verification Plan
1. **Automated Tests**: Run `pytest backend/tests` to ensure 100% test pass.
2. **Browser Verification**: Use `browser_subagent` to open the web app, test the authentication modal, test token ingestion, verify the cold email studio, and test email drafting and sending.
