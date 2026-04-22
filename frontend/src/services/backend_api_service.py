"""Backend API client with graceful fallback."""

from __future__ import annotations

import os

import httpx

from dto.api_dto import (
    AnalyzeRequestDto,
    AnalyzeResponseDto,
    SearchRequestDto,
    SearchResponseDto,
)
from services.mock_data_service import get_mock_vacancy


class BackendApiService:
    """Service that works with REST endpoints from project design."""

    def __init__(self) -> None:
        self.base_url = os.getenv("BACKEND_API_URL", "http://localhost:8000")
        self.timeout_seconds = 8.0

    def search_vacancy_ids(self, query: str) -> SearchResponseDto:
        """Call /api/v1/search and return vacancy identifiers."""
        payload = SearchRequestDto(query=query)
        with httpx.Client(base_url=self.base_url, timeout=self.timeout_seconds) as client:
            response = client.get("/api/v1/search", params=payload.model_dump())
            response.raise_for_status()
        return SearchResponseDto(vacancy_ids=response.json())

    def analyze_vacancies(self, profile: str, vacancy_ids: list[int]) -> AnalyzeResponseDto:
        """Call /api/v1/analyze and return analyzed vacancies."""
        payload = AnalyzeRequestDto(profile=profile, vacancy_ids=vacancy_ids)
        with httpx.Client(base_url=self.base_url, timeout=self.timeout_seconds) as client:
            response = client.post("/api/v1/analyze", json=payload.model_dump())
            response.raise_for_status()
        return AnalyzeResponseDto.model_validate(response.json())

    def get_vacancy_for_profile(self, profile: str) -> AnalyzeResponseDto:
        """Get analyzed vacancies or fallback to a local mock."""
        try:
            search_result = self.search_vacancy_ids(profile)
            return self.analyze_vacancies(profile, search_result.vacancy_ids)
        except (httpx.HTTPError, ValueError):
            mock_vacancy = get_mock_vacancy()
            return AnalyzeResponseDto(
                summary=(
                    "Пока backend API недоступен, поэтому показан демо-результат "
                    "по вакансии из mock-источника."
                ),
                vacancies=[mock_vacancy],
            )
