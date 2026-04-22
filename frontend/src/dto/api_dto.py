"""Transport DTOs for backend API integration."""

from __future__ import annotations

from pydantic import BaseModel

from dto.vacancy_dto import VacancyDto


class SearchRequestDto(BaseModel):
    """Request schema for GET /api/v1/search."""

    query: str


class SearchResponseDto(BaseModel):
    """Response schema from GET /api/v1/search."""

    vacancy_ids: list[int]


class AnalyzeRequestDto(BaseModel):
    """Request schema for POST /api/v1/analyze."""

    profile: str
    vacancy_ids: list[int]


class AnalyzeResponseDto(BaseModel):
    """Response schema from POST /api/v1/analyze."""

    summary: str
    vacancies: list[VacancyDto]
