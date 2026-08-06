"""Dashboard HTTP Basic authentication."""

from secrets import compare_digest

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBasic, HTTPBasicCredentials


security = HTTPBasic()


def require_admin(
    *,
    username: str,
    password: str,
):
    """Build a FastAPI dependency requiring admin basic auth."""

    def dependency(credentials: HTTPBasicCredentials = Depends(security)) -> str:
        username_ok = compare_digest(credentials.username, username)
        password_ok = compare_digest(credentials.password, password)
        if not (username_ok and password_ok):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid dashboard credentials",
                headers={"WWW-Authenticate": "Basic"},
            )
        return credentials.username

    return dependency
