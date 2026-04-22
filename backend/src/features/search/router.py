"""FastAPI router for vacancy search endpoints."""

from __future__ import annotations

from dataclasses import asdict

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, HttpUrl

from common.constants.api import (
    API_V1_PREFIX,
    ERROR_MESSAGE_BLANK_QUERY,
    ERROR_MESSAGE_SEARCH_UNAVAILABLE,
    HTTP_BAD_REQUEST,
    HTTP_NOT_FOUND,
    HTTP_INTERNAL_SERVER_ERROR,
    HTTP_UNPROCESSABLE_ENTITY,
    MAX_VACANCY_RESULTS,
    QUERY_MIN_LENGTH,
    SEARCH_ENDPOINT,
    SEARCH_TAG,
)
from common.schemas.api_error import ApiErrorResponse
from features.search.service import user_search

router = APIRouter(prefix=API_V1_PREFIX, tags=[SEARCH_TAG])


class VacancySearchResponse(BaseModel):
    """Public vacancy payload returned to the frontend."""

    id: int
    title: str
    company: str
    salary: str
    payment_frequency: str
    experience: str
    employment: str
    hiring_format: str
    schedule: str
    hours: str
    work_format: str
    skills: str
    url: HttpUrl
    description: str
    cosine_distance: float


@router.get(
    SEARCH_ENDPOINT,
    response_model=list[VacancySearchResponse],
    responses={
        HTTP_BAD_REQUEST: {
            "model": ApiErrorResponse,
            "description": "Invalid request payload.",
        },
        HTTP_NOT_FOUND: {
            "model": ApiErrorResponse,
            "description": "Endpoint not found.",
        },
        HTTP_UNPROCESSABLE_ENTITY: {
            "model": ApiErrorResponse,
            "description": "Validation failed.",
        },
        HTTP_INTERNAL_SERVER_ERROR: {
            "model": ApiErrorResponse,
            "description": "Internal server error.",
        },
    },
)
async def search_vacancies(
    query: str = Query(
        ...,
        min_length=QUERY_MIN_LENGTH,
        description="User profile or free-form query for vacancy matching.",
    ),
    limit: int = Query(
        default=MAX_VACANCY_RESULTS,
        ge=1,
        le=MAX_VACANCY_RESULTS,
        description="Maximum number of vacancies to return.",
    ),
) -> list[VacancySearchResponse]:
    """Return up to five most relevant vacancies with full details."""

    normalized_query = query.strip()
    if not normalized_query:
        raise HTTPException(
            status_code=HTTP_BAD_REQUEST, detail=ERROR_MESSAGE_BLANK_QUERY
        )
    try:
        search_result = await user_search(normalized_query, limit=limit)
    except RuntimeError as error:
        raise HTTPException(
            status_code=HTTP_INTERNAL_SERVER_ERROR,
            detail=ERROR_MESSAGE_SEARCH_UNAVAILABLE,
        ) from error
    return [
        VacancySearchResponse.model_validate(asdict(vacancy))
        for vacancy in search_result.vacancies
    ]
