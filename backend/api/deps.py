"""FastAPI dependencies."""

from __future__ import annotations

from typing import Any

import aiosqlite
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from backend.auth.jwt import decode_access_token
from backend.storage.database import get_db
from backend.storage.repositories import UserRepository

security = HTTPBearer(auto_error=False)


async def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(security),
    conn: aiosqlite.Connection = Depends(get_db),
) -> dict[str, Any]:
    if credentials is None or credentials.scheme.lower() != "bearer":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing or invalid Authorization header",
        )
    try:
        payload = decode_access_token(credentials.credentials)
        user_id = int(payload["sub"])
    except (ValueError, KeyError, TypeError) as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
        ) from exc

    user = await UserRepository(conn).get_by_id(user_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found",
        )
    return user


async def get_current_user_optional(
    credentials: HTTPAuthorizationCredentials | None = Depends(security),
    conn: aiosqlite.Connection = Depends(get_db),
) -> dict[str, Any] | None:
    if credentials is not None and credentials.scheme.lower() == "bearer":
        try:
            payload = decode_access_token(credentials.credentials)
            user_id = int(payload["sub"])
            user = await UserRepository(conn).get_by_id(user_id)
            if user:
                return user
        except Exception:
            pass
    return None
