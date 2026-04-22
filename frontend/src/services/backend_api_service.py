"""Backend API client with graceful fallback."""

from __future__ import annotations

import os

import httpx
from pydantic import ValidationError

from constants.api import (
    BACKEND_API_URL_ENV,
    BACKEND_REQUEST_RETRY_COUNT,
    BACKEND_TIMEOUT_SECONDS,
    DEFAULT_BACKEND_API_URL,
    HTTP_STATUS_NOT_FOUND,
    HTTP_STATUS_SERVER_ERROR_MIN,
    SEARCH_ENDPOINT,
)
from constants.messages import (
    DETAILS_PREFIX,
    ERROR_BACKEND_REQUEST_TEMPLATE,
    ERROR_BACKEND_UNAVAILABLE_TEMPLATE,
    ERROR_ENDPOINT_NOT_FOUND,
    ERROR_UNKNOWN_BACKEND,
    SUMMARY_EMPTY_RESULTS,
    SUMMARY_NETWORK_FAILURE,
    SUMMARY_SUCCESS,
)
from dto.api_dto import (
    AnalyzeResponseDto,
    ErrorResponseDto,
    SearchRequestDto,
    SearchResponseDto,
)


class BackendServiceError(Exception):
    """Raised when backend request fails with a known reason."""


class BackendApiService:
    """Service that works with REST endpoints from project design."""

    def __init__(self) -> None:
        self.base_url = os.getenv(BACKEND_API_URL_ENV, DEFAULT_BACKEND_API_URL)
        self.timeout_seconds = BACKEND_TIMEOUT_SECONDS

    def _parse_error_response(self, response: httpx.Response) -> str:
        """Extract human-readable error message from backend response."""

        try:
            payload = ErrorResponseDto.model_validate(response.json())
            if payload.details:
                return f"{payload.message}{DETAILS_PREFIX}{payload.details}"
            return payload.message
        except (ValueError, ValidationError):
            return response.text or ERROR_UNKNOWN_BACKEND

    def _handle_http_error(self, response: httpx.Response) -> None:
        """Raise a user-facing error based on HTTP status code."""

        if response.status_code < 400:
            return
        backend_message = self._parse_error_response(response)
        if response.status_code == HTTP_STATUS_NOT_FOUND:
            raise BackendServiceError(ERROR_ENDPOINT_NOT_FOUND)
        if response.status_code >= HTTP_STATUS_SERVER_ERROR_MIN:
            raise BackendServiceError(
                ERROR_BACKEND_UNAVAILABLE_TEMPLATE.format(
                    status_code=response.status_code,
                    details=backend_message,
                )
            )
        raise BackendServiceError(
            ERROR_BACKEND_REQUEST_TEMPLATE.format(
                status_code=response.status_code,
                details=backend_message,
            )
        )

    def search_vacancies(self, query: str) -> SearchResponseDto:
        """Call /api/v1/search and return full vacancies."""

        payload = SearchRequestDto(query=query.strip())
        response: httpx.Response | None = None
        last_error: httpx.RequestError | None = None
        attempts = BACKEND_REQUEST_RETRY_COUNT + 1
        with httpx.Client(
            base_url=self.base_url, timeout=self.timeout_seconds
        ) as client:
            for _ in range(attempts):
                try:
                    response = client.get(SEARCH_ENDPOINT, params=payload.model_dump())
                    last_error = None
                    break
                except httpx.RequestError as error:
                    last_error = error
        if response is None:
            if last_error is not None:
                raise last_error
            raise BackendServiceError(ERROR_UNKNOWN_BACKEND)
        self._handle_http_error(response)
        return SearchResponseDto.model_validate({"vacancies": response.json()})

    def get_vacancy_for_profile(self, profile: str) -> AnalyzeResponseDto:
        """Get relevant vacancies and return graceful error summary on failure."""

        try:
            search_result = self.search_vacancies(profile)
            if search_result.vacancies:
                return AnalyzeResponseDto(
                    summary=SUMMARY_SUCCESS,
                    vacancies=search_result.vacancies,
                )
            return AnalyzeResponseDto(
                summary=SUMMARY_EMPTY_RESULTS,
                vacancies=[],
            )
        except ValidationError:
            return AnalyzeResponseDto(
                summary=SUMMARY_NETWORK_FAILURE,
                vacancies=[],
            )
        except BackendServiceError:
            return AnalyzeResponseDto(
                summary=SUMMARY_NETWORK_FAILURE,
                vacancies=[],
            )
        except (httpx.RequestError, ValueError):
            return AnalyzeResponseDto(
                summary=SUMMARY_NETWORK_FAILURE,
                vacancies=[],
            )
