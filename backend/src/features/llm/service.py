"""OpenRouter service helpers for extracting vacancy filters from user text."""

from __future__ import annotations

import asyncio
import json
import os
import time
from typing import Any

import requests
from sqlalchemy import func, select

from common.constants.llm import (
    LLM_VALIDATION_RETRY_ATTEMPTS,
    VACANCY_OPTIONAL_KEYS,
    OPENROUTER_BASE_URL,
    OPENROUTER_MODEL,
    OPENROUTER_RETRY_ATTEMPTS,
    OPENROUTER_RETRY_BACKOFF_SECONDS,
    OPENROUTER_TIMEOUT_SECONDS,
    VACANCY_FILTER_KEYS,
    VACANCY_FILTERS_CONTEXT_TEMPLATE,
    VACANCY_FILTERS_SYSTEM_PROMPT_TEMPLATE,
)
from features.database.db import async_session_factory
from features.database.models import Vacancy
from features.llm.schemas import LlmAnswer

_FILTER_COLUMN_MAP = {
    "payment_frequency": Vacancy.payment_frequency,
    "experience": Vacancy.experience,
    "employment": Vacancy.employment,
    "hiring_format": Vacancy.hiring_format,
    "schedule": Vacancy.schedule,
    "hours": Vacancy.hours,
    "work_format": Vacancy.work_format,
}


def _get_openrouter_api_key() -> str:
    api_key = os.getenv("OPEN_ROUTER_API_KEY")
    if api_key and api_key.strip():
        return api_key.strip()
    msg = "OPEN_ROUTER_API_KEY is missing. Add it to environment variables."
    raise ValueError(msg)


def _build_payload(prompt: str, context: str) -> dict[str, Any]:
    return {
        "model": OPENROUTER_MODEL,
        "temperature": 0,
        "messages": [
            {"role": "system", "content": prompt},
            {"role": "user", "content": context},
        ],
    }


def _extract_content(data: dict[str, Any]) -> str:
    choices = data.get("choices")
    if not isinstance(choices, list) or not choices:
        raise ValueError("OpenRouter response does not contain choices.")
    message = choices[0].get("message")
    if not isinstance(message, dict):
        raise ValueError("OpenRouter response message is missing.")
    content = message.get("content")
    if not isinstance(content, str) or not content.strip():
        raise ValueError("OpenRouter response content is empty.")
    return content.strip()


def _strip_code_fences(text: str) -> str:
    cleaned = text.strip()
    if cleaned.startswith("```"):
        cleaned = cleaned[3:]
        if cleaned.startswith("json"):
            cleaned = cleaned[4:]
        cleaned = cleaned.strip()
        if cleaned.endswith("```"):
            cleaned = cleaned[:-3]
    return cleaned.strip()


def _parse_json_payload(raw_content: str) -> dict[str, Any]:
    normalized = _strip_code_fences(raw_content)
    parsed = json.loads(normalized)
    if not isinstance(parsed, dict):
        raise ValueError("LLM output must be a JSON object.")
    return parsed


def _empty_filter_object() -> dict[str, list[str]]:
    return {key: [] for key in VACANCY_FILTER_KEYS}


def _empty_filter_count_object() -> dict[str, dict[str, int]]:
    return {key: {} for key in VACANCY_FILTER_KEYS}


def _build_system_prompt(allowed_values: dict[str, list[str]]) -> str:
    allowed_values_json = json.dumps(allowed_values, ensure_ascii=False)
    return VACANCY_FILTERS_SYSTEM_PROMPT_TEMPLATE.format(
        allowed_values_json=allowed_values_json
    )


def _normalize_db_value(value: str | None) -> str | None:
    if value is None:
        return None
    normalized = value.strip()
    return normalized or None


def _validate_llm_payload(
    payload: dict[str, Any], allowed_values: dict[str, list[str]]
) -> list[str]:
    errors: list[str] = []
    required = set(VACANCY_FILTER_KEYS)
    optional = set(VACANCY_OPTIONAL_KEYS)
    payload_keys = set(payload.keys())
    if not required.issubset(payload_keys):
        errors.append("JSON must contain all required filter keys.")
    unknown = sorted(payload_keys - required - optional)
    if unknown:
        errors.append(f"JSON contains unknown keys: {', '.join(unknown)}.")

    role_keywords = payload.get("role_keywords", [])
    if not isinstance(role_keywords, list):
        errors.append("Field 'role_keywords' must be an array.")
    elif not all(isinstance(item, str) for item in role_keywords):
        errors.append("Field 'role_keywords' must contain only strings.")
    elif len(role_keywords) > 5:
        errors.append("Field 'role_keywords' must contain at most 5 items.")
    for key in VACANCY_FILTER_KEYS:
        value = payload.get(key)
        if not isinstance(value, list):
            errors.append(f"Field '{key}' must be an array.")
            continue
        allowed_set = set(allowed_values[key])
        invalid_values: list[str] = []
        for item in value:
            if not isinstance(item, dict):
                errors.append(f"Field '{key}' items must be objects.")
                continue
            if set(item.keys()) != {"value", "weight"}:
                errors.append(
                    f"Field '{key}' items must contain only 'value' and 'weight'."
                )
                continue
            raw_filter_value = item.get("value")
            raw_weight = item.get("weight")
            if not isinstance(raw_filter_value, str):
                errors.append(f"Field '{key}' item 'value' must be a string.")
                continue
            if not isinstance(raw_weight, int | float):
                errors.append(f"Field '{key}' item 'weight' must be numeric.")
                continue
            if not 0 <= float(raw_weight) <= 1:
                errors.append(f"Field '{key}' item 'weight' must be in range [0, 1].")
                continue
            if raw_filter_value not in allowed_set:
                invalid_values.append(raw_filter_value)
        if invalid_values:
            joined = ", ".join(invalid_values)
            errors.append(f"Field '{key}' has invalid values: {joined}.")
    return errors


def _build_retry_context(base_context: str, errors: list[str]) -> str:
    validation_errors = "\n".join(f"- {err}" for err in errors[:12])
    return (
        f"{base_context}\n\n"
        "Предыдущий ответ не прошел валидацию. "
        "Верни исправленный JSON по правилам.\n"
        f"Ошибки валидации:\n{validation_errors}"
    )


def _is_retryable_status(status_code: int) -> bool:
    return status_code == 429 or status_code >= 500


def _response_error_message(response: requests.Response) -> str:
    try:
        data = response.json()
        if isinstance(data, dict):
            error = data.get("error")
            if isinstance(error, dict) and isinstance(error.get("message"), str):
                return error["message"]
            if isinstance(error, str):
                return error
    except ValueError:
        pass
    return response.text.strip() or "Unknown OpenRouter error."


def _post_with_retry(
    headers: dict[str, str], payload: dict[str, Any]
) -> requests.Response:
    last_error: Exception | None = None
    for attempt in range(1, OPENROUTER_RETRY_ATTEMPTS + 1):
        try:
            response = requests.post(
                OPENROUTER_BASE_URL,
                headers=headers,
                json=payload,
                timeout=OPENROUTER_TIMEOUT_SECONDS,
            )
        except requests.RequestException as err:
            last_error = err
            if attempt == OPENROUTER_RETRY_ATTEMPTS:
                break
            time.sleep(OPENROUTER_RETRY_BACKOFF_SECONDS * attempt)
            continue

        if response.ok:
            return response
        if (
            _is_retryable_status(response.status_code)
            and attempt < OPENROUTER_RETRY_ATTEMPTS
        ):
            time.sleep(OPENROUTER_RETRY_BACKOFF_SECONDS * attempt)
            continue

        details = _response_error_message(response)
        msg = f"OpenRouter request failed ({response.status_code}): {details}"
        raise RuntimeError(msg)

    msg = f"OpenRouter request failed after retries: {last_error!r}"
    raise RuntimeError(msg)


def get_llm_answer_service(prompt: str, context: str) -> LlmAnswer:
    """Call OpenRouter chat completions and parse JSON from the first choice."""
    api_key = _get_openrouter_api_key()
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }
    payload = _build_payload(prompt, context)
    response = _post_with_retry(headers, payload)
    data = response.json()
    raw_content = _extract_content(data)
    payload = _parse_json_payload(raw_content)
    model = str(data.get("model", OPENROUTER_MODEL))
    return LlmAnswer(model=model, raw_content=raw_content, payload=payload)


async def build_vacancy_filter_allowed_values() -> dict[str, list[str]]:
    """Build allowed filter values from unique vacancy fields in PostgreSQL."""
    counts = await build_vacancy_filter_value_counts()
    return {key: sorted(counts[key]) for key in VACANCY_FILTER_KEYS}


async def build_vacancy_filter_value_counts() -> dict[str, dict[str, int]]:
    """Build ``value -> count`` maps for each filter field from PostgreSQL."""
    allowed_values = _empty_filter_count_object()
    async with async_session_factory() as session:
        for key in VACANCY_FILTER_KEYS:
            column = _FILTER_COLUMN_MAP[key]
            stmt = (
                select(column, func.count(column))
                .where(column.isnot(None))
                .group_by(column)
                .order_by(column)
            )
            result = await session.execute(stmt)
            value_counts: dict[str, int] = {}
            for value, count in result.all():
                normalized = _normalize_db_value(value)
                if normalized is not None:
                    value_counts[normalized] = int(count)
            allowed_values[key] = value_counts
    return allowed_values


async def get_vacancy_filters_from_text_async(user_message: str) -> dict[str, Any]:
    """Build DB-based prompt, request filters from LLM, and validate response."""
    allowed_values = await build_vacancy_filter_allowed_values()
    prompt = _build_system_prompt(allowed_values)
    base_context = VACANCY_FILTERS_CONTEXT_TEMPLATE.format(
        user_message=user_message.strip()
    )
    context = base_context
    errors: list[str] = []
    for _ in range(LLM_VALIDATION_RETRY_ATTEMPTS):
        try:
            answer = get_llm_answer_service(prompt, context)
        except ValueError as error:
            errors = [str(error)]
        else:
            errors = _validate_llm_payload(answer.payload, allowed_values)
            if not errors:
                return answer.payload
        context = _build_retry_context(base_context, errors)
    details = "; ".join(errors) if errors else "Unknown validation error."
    raise RuntimeError(f"LLM response validation failed: {details}")


def get_vacancy_filters_from_text(user_message: str) -> dict[str, Any]:
    """Synchronous wrapper for LLM-based vacancy filter extraction."""
    try:
        asyncio.get_running_loop()
    except RuntimeError:
        return asyncio.run(get_vacancy_filters_from_text_async(user_message))
    msg = "Use get_vacancy_filters_from_text_async() inside async context."
    raise RuntimeError(msg)
