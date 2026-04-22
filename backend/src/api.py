"""FastAPI application entrypoint for frontend integration."""

from __future__ import annotations

from fastapi import FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError, ResponseValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from common.constants.api import (
    APP_TITLE,
    APP_VERSION,
    ERROR_CODE_HTTP,
    ERROR_CODE_INTERNAL,
    ERROR_CODE_NOT_FOUND,
    ERROR_CODE_REQUEST_VALIDATION,
    ERROR_CODE_RESPONSE_VALIDATION,
    ERROR_MESSAGE_HTTP,
    ERROR_MESSAGE_INTERNAL,
    ERROR_MESSAGE_NOT_FOUND,
    ERROR_MESSAGE_REQUEST_VALIDATION,
    ERROR_MESSAGE_RESPONSE_VALIDATION,
    HTTP_NOT_FOUND,
    HTTP_INTERNAL_SERVER_ERROR,
    HTTP_UNPROCESSABLE_ENTITY,
)
from common.schemas.api_error import ApiErrorResponse
from features.search.router import router as search_router

app = FastAPI(title=APP_TITLE, version=APP_VERSION)
app.include_router(search_router)


@app.exception_handler(RequestValidationError)
async def handle_request_validation_error(
    _: Request, exc: RequestValidationError
) -> JSONResponse:
    """Return a consistent payload for invalid incoming data."""

    payload = ApiErrorResponse(
        error_code=ERROR_CODE_REQUEST_VALIDATION,
        message=ERROR_MESSAGE_REQUEST_VALIDATION,
        details=exc.errors(),
    )
    return JSONResponse(
        status_code=HTTP_UNPROCESSABLE_ENTITY, content=payload.model_dump()
    )


@app.exception_handler(ResponseValidationError)
async def handle_response_validation_error(
    _: Request, exc: ResponseValidationError
) -> JSONResponse:
    """Return a generic payload when outgoing response is invalid."""

    payload = ApiErrorResponse(
        error_code=ERROR_CODE_RESPONSE_VALIDATION,
        message=ERROR_MESSAGE_RESPONSE_VALIDATION,
        details=str(exc),
    )
    return JSONResponse(
        status_code=HTTP_INTERNAL_SERVER_ERROR, content=payload.model_dump()
    )


@app.exception_handler(StarletteHTTPException)
async def handle_http_error(_: Request, exc: StarletteHTTPException) -> JSONResponse:
    """Map HTTP errors to standardized API responses."""

    if exc.status_code == HTTP_NOT_FOUND:
        payload = ApiErrorResponse(
            error_code=ERROR_CODE_NOT_FOUND,
            message=ERROR_MESSAGE_NOT_FOUND,
            details=str(exc.detail),
        )
        return JSONResponse(status_code=HTTP_NOT_FOUND, content=payload.model_dump())
    if exc.status_code == HTTP_UNPROCESSABLE_ENTITY:
        payload = ApiErrorResponse(
            error_code=ERROR_CODE_REQUEST_VALIDATION,
            message=ERROR_MESSAGE_REQUEST_VALIDATION,
            details=str(exc.detail),
        )
        return JSONResponse(
            status_code=HTTP_UNPROCESSABLE_ENTITY, content=payload.model_dump()
        )
    payload = ApiErrorResponse(
        error_code=ERROR_CODE_HTTP,
        message=ERROR_MESSAGE_HTTP,
        details=str(exc.detail),
    )
    return JSONResponse(status_code=exc.status_code, content=payload.model_dump())


@app.exception_handler(HTTPException)
async def handle_fastapi_http_error(_: Request, exc: HTTPException) -> JSONResponse:
    """Handle FastAPI HTTP exceptions raised in business handlers."""

    payload = ApiErrorResponse(
        error_code=ERROR_CODE_HTTP,
        message=ERROR_MESSAGE_HTTP,
        details=str(exc.detail),
    )
    return JSONResponse(status_code=exc.status_code, content=payload.model_dump())


@app.exception_handler(Exception)
async def handle_unexpected_error(_: Request, exc: Exception) -> JSONResponse:
    """Handle unexpected server-side failures."""

    payload = ApiErrorResponse(
        error_code=ERROR_CODE_INTERNAL,
        message=ERROR_MESSAGE_INTERNAL,
        details=str(exc),
    )
    return JSONResponse(
        status_code=HTTP_INTERNAL_SERVER_ERROR, content=payload.model_dump()
    )
