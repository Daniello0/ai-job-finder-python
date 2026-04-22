"""Transport DTOs for backend API integration."""

from __future__ import annotations

from pydantic import BaseModel, Field

from constants.api import SEARCH_QUERY_MAX_LENGTH, SEARCH_QUERY_MIN_LENGTH
from dto.vacancy_dto import VacancyDto


class SearchRequestDto(BaseModel):
    """Request schema for GET /api/v1/search."""

    query: str = Field(
        min_length=SEARCH_QUERY_MIN_LENGTH, max_length=SEARCH_QUERY_MAX_LENGTH
    )


class SearchResponseDto(BaseModel):
    """Response schema from GET /api/v1/search."""

    vacancies: list[VacancyDto]


class AnalyzeResponseDto(BaseModel):
    """UI-level response assembled from backend search results."""

    summary: str
    vacancies: list[VacancyDto]


class ErrorResponseDto(BaseModel):
    """Backend error payload schema."""

    error_code: str
    message: str
    details: str | list[dict[str, object]] | None = None
