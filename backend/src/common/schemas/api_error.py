"""Shared API error schema for all FastAPI handlers."""

from __future__ import annotations

from pydantic import BaseModel


class ApiErrorResponse(BaseModel):
    """Standardized error payload returned by backend API."""

    error_code: str
    message: str
    details: str | list[dict[str, object]] | None = None
