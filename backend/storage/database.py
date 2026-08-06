"""Database connection helpers (re-export for clarity)."""

from backend.storage import connect, get_db

__all__ = ["connect", "get_db"]
