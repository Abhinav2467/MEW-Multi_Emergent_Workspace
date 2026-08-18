"""Auth routes: Google OAuth + JWT."""

from __future__ import annotations

from typing import Any

import aiosqlite
from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.security import HTTPAuthorizationCredentials

from backend.api.deps import get_current_user, security
from backend.auth.google_oauth import build_auth_url, exchange_code_for_tokens
from backend.auth.jwt import create_access_token, decode_access_token
from backend.models.schemas import AuthUrlResponse, TokenResponse, UserOut
from backend.storage.database import get_db
from backend.storage.repositories import UserRepository

router = APIRouter(prefix="/auth", tags=["auth"])


def _user_out(user: dict[str, Any]) -> UserOut:
    return UserOut(
        id=user["id"],
        email=user["email"],
        name=user.get("name"),
        has_gmail_token=bool(user.get("gmail_tokens_json")),
    )


from fastapi import APIRouter, Depends, HTTPException, Query, Request, Response
from fastapi.responses import HTMLResponse, JSONResponse

@router.get("/google", response_model=AuthUrlResponse)
async def google_auth_url(
    redirect_uri: str | None = Query(None),
    state: str | None = Query(None),
) -> AuthUrlResponse:
    try:
        url = build_auth_url(state=state, redirect_uri=redirect_uri)
    except Exception:
        from urllib.parse import urlencode
        client_id = "687818556583-mrmcf9jupect5reccpfbsc3lettdr3rd.apps.googleusercontent.com"
        scopes = "openid email profile https://www.googleapis.com/auth/gmail.compose https://www.googleapis.com/auth/gmail.send"
        params = {
            "client_id": client_id,
            "redirect_uri": redirect_uri or "http://localhost",
            "response_type": "code",
            "scope": scopes,
            "access_type": "offline",
            "prompt": "consent",
        }
        if state:
            params["state"] = state
        url = f"https://accounts.google.com/o/oauth2/v2/auth?{urlencode(params)}"
    return AuthUrlResponse(url=url)


@router.get("/callback")
async def google_callback(
    request: Request,
    code: str = Query(...),
    redirect_uri: str | None = Query(None),
    state: str | None = Query(None),
    format: str | None = Query(None),
    conn: aiosqlite.Connection = Depends(get_db),
):
    try:
        oauth = await exchange_code_for_tokens(code, redirect_uri=redirect_uri)
    except Exception as exc:
        raise HTTPException(status_code=400, detail=f"OAuth exchange failed: {exc}") from exc

    user = await UserRepository(conn).upsert_google_user(
        google_id=oauth["google_id"],
        email=oauth["email"],
        name=oauth.get("name"),
        gmail_tokens_json=oauth["gmail_tokens_json"],
        google_refresh_token=oauth.get("google_refresh_token"),
    )
    token = create_access_token(user_id=user["id"], email=user["email"])
    user_out = _user_out(user)

    # If programmatic API request explicitly asked for JSON
    accept_header = request.headers.get("accept", "")
    if format == "json" or ("application/json" in accept_header and "text/html" not in accept_header):
        return TokenResponse(access_token=token, user=user_out)

    # Determine return frontend destination if available
    return_dest = "http://localhost:3000"
    if state and state.startswith("http"):
        return_dest = state
    elif redirect_uri and redirect_uri.startswith("http") and not redirect_uri.endswith("/auth/callback"):
        return_dest = redirect_uri

    user_name = user_out.name or "Candidate"
    user_email = user_out.email or ""

    html_content = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Google Authentication Successful | MEW Workspace</title>
    <link rel="preconnect" href="https://fonts.googleapis.com">
    <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&family=JetBrains+Mono:wght@400;500;600&display=swap" rel="stylesheet">
    <link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Material+Symbols+Outlined:opsz,wght,FILL,GRAD@20..48,100..700,0..1,-50..200" />
    <script src="https://cdn.tailwindcss.com"></script>
    <script>
        tailwind.config = {{
            theme: {{
                extend: {{
                    fontFamily: {{
                        sans: ['Inter', 'sans-serif'],
                        mono: ['JetBrains Mono', 'monospace'],
                    }},
                    colors: {{
                        primary: '#10b981',
                        accent: '#8b5cf6',
                        dark: '#08090a',
                    }}
                }}
            }}
        }}
    </script>
</head>
<body class="bg-[#08090a] text-slate-100 min-h-screen flex items-center justify-center p-4 font-sans selection:bg-emerald-500/30">
    <div class="max-w-md w-full bg-slate-900/90 border border-slate-800/80 rounded-2xl p-8 shadow-2xl backdrop-blur-xl relative overflow-hidden text-center">
        <!-- Glow accents -->
        <div class="absolute -top-24 -left-24 w-48 h-48 bg-emerald-500/15 rounded-full blur-3xl pointer-events-none"></div>
        <div class="absolute -bottom-24 -right-24 w-48 h-48 bg-purple-500/15 rounded-full blur-3xl pointer-events-none"></div>

        <!-- Success Icon -->
        <div class="w-16 h-16 rounded-full bg-emerald-500/10 border border-emerald-500/30 text-emerald-400 flex items-center justify-center mx-auto mb-5 shadow-inner">
            <span class="material-symbols-outlined text-3xl">verified_user</span>
        </div>

        <h1 class="text-2xl font-bold text-white tracking-tight mb-2">Google Connected!</h1>
        <p id="status-msg" class="text-sm text-slate-400 mb-6">Your Gmail account is linked for live cold outreach.</p>

        <!-- User Badge -->
        <div class="bg-slate-800/60 border border-slate-700/50 rounded-xl p-3.5 mb-6 text-left flex items-center space-x-3.5">
            <div class="w-10 h-10 rounded-full bg-gradient-to-tr from-emerald-600 to-teal-500 text-white font-bold flex items-center justify-center text-base shrink-0 shadow-md">
                {user_name[0].upper() if user_name else 'U'}
            </div>
            <div class="min-w-0 flex-1">
                <div class="font-semibold text-slate-200 text-sm truncate">{user_name}</div>
                <div class="text-xs text-emerald-400 truncate">{user_email}</div>
            </div>
            <span class="material-symbols-outlined text-emerald-400 text-lg">check_circle</span>
        </div>

        <!-- Token Box -->
        <div class="mb-6 text-left">
            <label class="block text-xs font-semibold text-slate-400 mb-1.5 uppercase tracking-wider">Access Token Key</label>
            <div class="relative">
                <input id="token-input" type="text" readonly value="{token}" class="w-full bg-slate-950/80 border border-slate-800 rounded-xl px-3.5 py-2.5 text-xs text-slate-300 font-mono focus:outline-none focus:border-emerald-500/50 pr-24 select-all shadow-inner" />
                <button id="btn-copy-token" onclick="copyToken()" class="absolute right-1.5 top-1.5 bottom-1.5 px-3 bg-emerald-500/15 hover:bg-emerald-500/25 border border-emerald-500/30 text-emerald-300 text-xs rounded-lg font-medium transition flex items-center space-x-1">
                    <span id="copy-icon" class="material-symbols-outlined text-sm">content_copy</span>
                    <span id="copy-text">Copy</span>
                </button>
            </div>
        </div>

        <!-- Action Button -->
        <button id="btn-return" onclick="returnToApp()" class="w-full py-3 px-4 bg-gradient-to-r from-emerald-600 to-teal-600 hover:from-emerald-500 hover:to-teal-500 text-white text-sm font-semibold rounded-xl transition shadow-lg shadow-emerald-900/30 flex items-center justify-center space-x-2">
            <span>Return to Workspace</span>
            <span class="material-symbols-outlined text-base">arrow_forward</span>
        </button>

        <p class="text-[11px] text-slate-500 mt-4">This window will close automatically once synced with your app.</p>
    </div>

    <script>
        const AUTH_DATA = {{
            type: 'MEW_GOOGLE_AUTH_SUCCESS',
            token: "{token}",
            user: {{
                id: {user_out.id},
                email: "{user_email}",
                name: "{user_name}",
                has_gmail_token: true
            }}
        }};

        function postToOpener() {{
            if (window.opener && !window.opener.closed) {{
                try {{
                    window.opener.postMessage(AUTH_DATA, '*');
                    document.getElementById('status-msg').innerText = '✓ Workspace connected! Closing window...';
                    setTimeout(() => {{
                        window.close();
                    }}, 1000);
                    return true;
                }} catch (e) {{
                    console.warn('postMessage to opener warning:', e);
                }}
            }}
            return false;
        }}

        function returnToApp() {{
            if (!postToOpener()) {{
                const dest = "{return_dest}";
                const targetUrl = dest.includes('#') ? dest : (dest + '#token=' + encodeURIComponent(AUTH_DATA.token));
                window.location.replace(targetUrl);
            }}
        }}

        function copyToken() {{
            const input = document.getElementById('token-input');
            input.select();
            navigator.clipboard.writeText(AUTH_DATA.token).then(() => {{
                document.getElementById('copy-text').innerText = 'Copied!';
                document.getElementById('copy-icon').innerText = 'done';
                setTimeout(() => {{
                    document.getElementById('copy-text').innerText = 'Copy';
                    document.getElementById('copy-icon').innerText = 'content_copy';
                }}, 2000);
            }}).catch(() => {{
                document.execCommand('copy');
                document.getElementById('copy-text').innerText = 'Copied!';
            }});
        }}

        // Auto post message immediately on load
        window.addEventListener('DOMContentLoaded', () => {{
            postToOpener();
        }});
    </script>
</body>
</html>"""
    return HTMLResponse(content=html_content)


@router.get("/me", response_model=UserOut)
async def me(user: dict[str, Any] = Depends(get_current_user)) -> UserOut:
    return _user_out(user)


@router.get("/active-session")
async def active_session(
    credentials: HTTPAuthorizationCredentials | None = Depends(security),
    conn: aiosqlite.Connection = Depends(get_db),
) -> dict[str, Any]:
    """Check if an active authenticated user session exists strictly via Bearer JWT token."""
    if credentials is not None and credentials.scheme.lower() == "bearer":
        try:
            payload = decode_access_token(credentials.credentials)
            user_id = int(payload["sub"])
            user = await UserRepository(conn).get_by_id(user_id)
            if user:
                token = create_access_token(user_id=user["id"], email=user["email"])
                return {
                    "authenticated": True,
                    "access_token": token,
                    "user": _user_out(user),
                }
        except Exception:
            pass

    return {"authenticated": False, "user": None, "access_token": None}
