"""Google OAuth with Gmail compose/send scopes."""

from __future__ import annotations

import json
from typing import Any
from urllib.parse import urlencode

import httpx

from backend.config import resolve_google_oauth_client

GOOGLE_AUTH_URL = "https://accounts.google.com/o/oauth2/v2/auth"
GOOGLE_TOKEN_URL = "https://oauth2.googleapis.com/token"
GOOGLE_USERINFO_URL = "https://www.googleapis.com/oauth2/v3/userinfo"

SCOPES = [
    "openid",
    "email",
    "profile",
    "https://www.googleapis.com/auth/gmail.compose",
    "https://www.googleapis.com/auth/gmail.send",
]


def build_auth_url(state: str | None = None) -> str:
    oauth = resolve_google_oauth_client()

    params: dict[str, str] = {
        "client_id": oauth.client_id,
        "redirect_uri": oauth.redirect_uri,
        "response_type": "code",
        "scope": " ".join(SCOPES),
        "access_type": "offline",
        "prompt": "consent",
        "include_granted_scopes": "true",
    }
    if state:
        params["state"] = state
    return f"{GOOGLE_AUTH_URL}?{urlencode(params)}"


async def exchange_code_for_tokens(code: str) -> dict[str, Any]:
    """Exchange authorization code for tokens and user info."""
    oauth = resolve_google_oauth_client()

    redirect_uris_to_try = [
        oauth.redirect_uri,
        "http://localhost",
        "http://localhost:8000/auth/callback",
        "https://developers.google.com/oauthplayground",
        "urn:ietf:wg:oauth:2.0:oob",
        "http://localhost:3000/auth/callback"
    ]
    token_resp = None
    last_exc = None

    async with httpx.AsyncClient(timeout=30.0) as client:
        for r_uri in redirect_uris_to_try:
            try:
                resp = await client.post(
                    GOOGLE_TOKEN_URL,
                    data={
                        "code": code,
                        "client_id": oauth.client_id,
                        "client_secret": oauth.client_secret,
                        "redirect_uri": r_uri,
                        "grant_type": "authorization_code",
                    },
                )
                resp.raise_for_status()
                token_resp = resp
                break
            except Exception as exc:
                last_exc = exc
                continue

        if not token_resp:
            raise last_exc or ValueError("Failed to exchange code across all redirect URIs")

        tokens = token_resp.json()

        userinfo_resp = await client.get(
            GOOGLE_USERINFO_URL,
            headers={"Authorization": f"Bearer {tokens['access_token']}"},
        )
        userinfo_resp.raise_for_status()
        userinfo = userinfo_resp.json()

    # Shape compatible with google.oauth2.credentials.Credentials.from_authorized_user_info
    gmail_creds = {
        "token": tokens.get("access_token"),
        "refresh_token": tokens.get("refresh_token"),
        "token_uri": GOOGLE_TOKEN_URL,
        "client_id": oauth.client_id,
        "client_secret": oauth.client_secret,
        "scopes": SCOPES,
        "expiry": None,
    }

    return {
        "google_id": userinfo["sub"],
        "email": userinfo.get("email", ""),
        "name": userinfo.get("name"),
        "gmail_tokens_json": json.dumps(gmail_creds),
        "google_refresh_token": tokens.get("refresh_token"),
        "raw_tokens": tokens,
        "userinfo": userinfo,
    }


async def refresh_google_access_token(refresh_token: str) -> dict[str, Any]:
    """Silently fetch a fresh access token using a stored refresh_token."""
    oauth = resolve_google_oauth_client()
    async with httpx.AsyncClient(timeout=30.0) as client:
        resp = await client.post(
            GOOGLE_TOKEN_URL,
            data={
                "client_id": oauth.client_id,
                "client_secret": oauth.client_secret,
                "refresh_token": refresh_token,
                "grant_type": "refresh_token",
            },
        )
        resp.raise_for_status()
        return resp.json()
