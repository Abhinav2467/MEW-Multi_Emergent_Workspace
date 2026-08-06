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


@router.get("/google", response_model=AuthUrlResponse)
async def google_auth_url() -> AuthUrlResponse:
    try:
        url = build_auth_url()
    except ValueError as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc
    return AuthUrlResponse(url=url)


@router.get("/callback", response_model=TokenResponse)
async def google_callback(
    code: str = Query(...),
    conn: aiosqlite.Connection = Depends(get_db),
) -> TokenResponse:
    try:
        oauth = await exchange_code_for_tokens(code)
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
    return TokenResponse(access_token=token, user=_user_out(user))


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
