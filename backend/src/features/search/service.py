"""Orchestrate user search: LLM filter extraction then filtered embedding search."""

from __future__ import annotations

import asyncio
from typing import Any

from common.constants.embedding import DEFAULT_SIMILARITY_TOP_K
from common.constants.llm import VACANCY_FILTER_KEYS
from common.constants.search import (
    DEFAULT_MAX_VALUES_PER_FILTER,
    DEFAULT_MIN_FILTERED_CANDIDATES,
    DOMAIN_BOOST_STEP,
    PROTECTED_RELAX_FILTER_KEYS,
    PROTECTED_RELAX_WEIGHT_PENALTY,
    ROLE_KEYWORDS_HARD_LOCK,
)
from sqlalchemy import Select, func, or_, select

from features.database.db import async_session_factory
from features.database.models import Vacancy
from features.embedding.schemas import SimilaritySearchResult
from features.embedding.similarity_search_service import similarity_search
from features.llm.service import (
    build_vacancy_filter_value_counts,
    get_vacancy_filters_from_text_async,
)
from features.search.schemas import FilterRelaxStep, UserSearchResult

_FILTER_COLUMN_MAP = {
    "payment_frequency": Vacancy.payment_frequency,
    "experience": Vacancy.experience,
    "employment": Vacancy.employment,
    "hiring_format": Vacancy.hiring_format,
    "schedule": Vacancy.schedule,
    "hours": Vacancy.hours,
    "work_format": Vacancy.work_format,
}

_DOMAIN_KEYWORDS = {
    "horeca": ("бариста", "кофе", "кофейн", "десерт", "кондитер", "пекар", "кухн"),
    "it": ("python", "backend", "developer", "разработ", "программист", "fastapi"),
    "logistics": ("склад", "логист", "комплектов", "кладов", "грузчик"),
}


def _empty_filters() -> dict[str, list[str]]:
    return {key: [] for key in VACANCY_FILTER_KEYS}


def _empty_weighted_filters() -> dict[str, list[dict[str, float | str]]]:
    return {key: [] for key in VACANCY_FILTER_KEYS}


def _clone_non_empty(filters: dict[str, list[str]]) -> dict[str, list[str]]:
    return {key: list(values) for key, values in filters.items() if values}


def _empty_filter_counts() -> dict[str, dict[str, int]]:
    return {key: {} for key in VACANCY_FILTER_KEYS}


def _with_all_count_keys(
    counts: dict[str, dict[str, int]],
) -> dict[str, dict[str, int]]:
    completed = _empty_filter_counts()
    completed.update(counts)
    return completed


def _with_all_keys(filters: dict[str, list[str]]) -> dict[str, list[str]]:
    completed = _empty_filters()
    completed.update(filters)
    return completed


def _normalize_weighted_filters(
    payload: dict[str, Any],
) -> dict[str, list[tuple[str, float]]]:
    normalized: dict[str, list[tuple[str, float]]] = {
        key: [] for key in VACANCY_FILTER_KEYS
    }
    for key in VACANCY_FILTER_KEYS:
        items = payload.get(key, [])
        if not isinstance(items, list):
            msg = f"Filter '{key}' must be a list of objects."
            raise ValueError(msg)
        weight_by_value: dict[str, float] = {}
        for item in items:
            if not isinstance(item, dict):
                continue
            raw_value = item.get("value")
            raw_weight = item.get("weight")
            if not isinstance(raw_value, str) or not raw_value.strip():
                continue
            if not isinstance(raw_weight, int | float):
                continue
            value = raw_value.strip()
            weight = float(raw_weight)
            weight_by_value[value] = max(weight_by_value.get(value, 0.0), weight)
        normalized[key] = sorted(
            ((value, weight) for value, weight in weight_by_value.items()),
            key=lambda item: item[1],
            reverse=True,
        )[:DEFAULT_MAX_VALUES_PER_FILTER]
    return normalized


def _serialize_weighted_filters(
    filters: dict[str, list[tuple[str, float]]],
) -> dict[str, list[dict[str, float | str]]]:
    result = _empty_weighted_filters()
    for key in VACANCY_FILTER_KEYS:
        result[key] = [
            {"value": value, "weight": round(weight, 4)}
            for value, weight in filters[key]
        ]
    return result


def _plain_filters_from_weighted(
    filters: dict[str, list[tuple[str, float]]],
) -> dict[str, list[str]]:
    plain = _empty_filters()
    for key in VACANCY_FILTER_KEYS:
        plain[key] = [value for value, _ in filters[key]]
    return plain


def _apply_filters(
    stmt: Select[tuple[int]], filters: dict[str, list[str]]
) -> Select[tuple[int]]:
    for key, values in filters.items():
        if values:
            stmt = stmt.where(_FILTER_COLUMN_MAP[key].in_(values))
    return stmt


def _normalize_role_keywords(payload: dict[str, Any]) -> list[str]:
    role_keywords = payload.get("role_keywords", [])
    if not isinstance(role_keywords, list):
        return []
    normalized = sorted(
        {
            item.strip().lower()
            for item in role_keywords
            if isinstance(item, str) and item.strip()
        }
    )
    return normalized[:5]


def _apply_role_keywords(
    stmt: Select[tuple[int]], role_keywords: list[str]
) -> Select[tuple[int]]:
    if not ROLE_KEYWORDS_HARD_LOCK or not role_keywords:
        return stmt
    clauses = [
        or_(
            Vacancy.title.ilike(f"%{keyword}%"),
            Vacancy.skills.ilike(f"%{keyword}%"),
        )
        for keyword in role_keywords
    ]
    return stmt.where(or_(*clauses))


async def _count_filtered_candidates(
    filters: dict[str, list[str]],
    *,
    role_keywords: list[str],
) -> int:
    stmt = select(func.count(Vacancy.id))
    stmt = _apply_filters(stmt, filters)
    stmt = _apply_role_keywords(stmt, role_keywords)
    async with async_session_factory() as session:
        count = await session.scalar(stmt)
    return int(count or 0)


def _build_selected_value_counts(
    filters: dict[str, list[tuple[str, float]]],
    value_counts: dict[str, dict[str, int]],
) -> dict[str, dict[str, int]]:
    selected_counts = _empty_filter_counts()
    for key in VACANCY_FILTER_KEYS:
        for value, _ in filters.get(key, []):
            selected_counts[key][value] = value_counts.get(key, {}).get(value, 0)
    return selected_counts


def _build_field_drop_order(
    weighted_filters: dict[str, list[tuple[str, float]]],
    protected_keys: set[str],
) -> list[tuple[str, float]]:
    fields: list[tuple[str, float]] = []
    for key in VACANCY_FILTER_KEYS:
        values = weighted_filters[key]
        if values:
            field_weight = max(weight for _, weight in values)
            fields.append((key, field_weight))

    def _effective_weight(item: tuple[str, float]) -> float:
        key, weight = item
        if key in protected_keys:
            return min(1.0, weight + PROTECTED_RELAX_WEIGHT_PENALTY)
        return weight

    return sorted(
        fields,
        key=lambda item: (
            _effective_weight(item),
            item[0],
        ),
    )


async def _relax_filters(
    weighted_filters: dict[str, list[tuple[str, float]]],
    *,
    value_counts: dict[str, dict[str, int]],
    role_keywords: list[str],
    min_candidates: int,
) -> tuple[dict[str, list[str]], dict[str, list[str]], list[FilterRelaxStep], int]:
    active_filters = _clone_non_empty(_plain_filters_from_weighted(weighted_filters))
    weighted_by_key = {key: list(values) for key, values in weighted_filters.items()}
    dropped_filters = _empty_filters()
    relax_steps: list[FilterRelaxStep] = []
    candidate_count = await _count_filtered_candidates(
        active_filters, role_keywords=role_keywords
    )
    if candidate_count >= min_candidates:
        return (
            _with_all_keys(active_filters),
            dropped_filters,
            relax_steps,
            candidate_count,
        )

    protected_keys = set(PROTECTED_RELAX_FILTER_KEYS)
    drop_order = _build_field_drop_order(weighted_by_key, protected_keys)
    for step_index, (key, weight) in enumerate(drop_order, start=1):
        removed_values = [value for value, _ in weighted_by_key.get(key, [])]
        if not removed_values:
            continue
        candidates_before = candidate_count
        dropped_filters[key].extend(removed_values)
        active_filters.pop(key, None)
        candidate_count = await _count_filtered_candidates(
            active_filters, role_keywords=role_keywords
        )
        removed_total_count = sum(
            value_counts.get(key, {}).get(value, 0) for value in removed_values
        )
        relax_steps.append(
            FilterRelaxStep(
                step=step_index,
                filter_key=key,
                filter_value=", ".join(removed_values),
                removed_weight=weight,
                value_count_in_db=removed_total_count,
                candidates_before=candidates_before,
                candidates_after=candidate_count,
            )
        )
        if candidate_count >= min_candidates:
            break
    return _with_all_keys(active_filters), dropped_filters, relax_steps, candidate_count


def _query_domain_keywords(query: str, role_keywords: list[str]) -> set[str]:
    query_lower = query.lower()
    matched: set[str] = set(role_keywords)
    for keywords in _DOMAIN_KEYWORDS.values():
        if any(keyword in query_lower for keyword in keywords):
            matched.update(keywords)
    return matched


def _rank_with_domain_boost(
    user_query: str,
    role_keywords: list[str],
    vacancies: list[SimilaritySearchResult],
) -> list[SimilaritySearchResult]:
    keywords = _query_domain_keywords(user_query, role_keywords)
    if not keywords:
        return vacancies
    scored: list[tuple[float, float, SimilaritySearchResult]] = []
    for vacancy in vacancies:
        haystack = f"{vacancy.title} {vacancy.skills}".lower()
        matches = sum(1 for keyword in keywords if keyword in haystack)
        boosted_distance = vacancy.cosine_distance - DOMAIN_BOOST_STEP * min(matches, 3)
        scored.append((boosted_distance, vacancy.cosine_distance, vacancy))
    scored.sort(key=lambda item: (item[0], item[1]))
    return [item[2] for item in scored]


async def user_search(
    user_query: str,
    *,
    limit: int = DEFAULT_SIMILARITY_TOP_K,
    min_candidates: int = DEFAULT_MIN_FILTERED_CANDIDATES,
) -> UserSearchResult:
    """
    Run user-facing search flow:
    1) infer structured filters via LLM,
    2) relax low-weight fields until enough candidates,
    3) run embedding similarity search within filtered vacancy subset.
    """
    stripped_query = user_query.strip()
    if not stripped_query:
        return UserSearchResult(
            user_query="",
            role_keywords=[],
            llm_filters=_empty_weighted_filters(),
            all_value_counts=_empty_filter_counts(),
            selected_value_counts=_empty_filter_counts(),
            applied_filters=_empty_filters(),
            dropped_filters=_empty_filters(),
            relax_steps=[],
            candidate_count=0,
            vacancies=[],
        )
    raw_filters = await get_vacancy_filters_from_text_async(stripped_query)
    role_keywords = _normalize_role_keywords(raw_filters)
    llm_weighted_filters = _normalize_weighted_filters(raw_filters)
    value_counts = await build_vacancy_filter_value_counts()
    selected_value_counts = _build_selected_value_counts(
        llm_weighted_filters, value_counts
    )
    (
        applied_filters,
        dropped_filters,
        relax_steps,
        candidate_count,
    ) = await _relax_filters(
        llm_weighted_filters,
        value_counts=value_counts,
        role_keywords=role_keywords,
        min_candidates=min_candidates,
    )
    vacancies = await similarity_search(
        stripped_query,
        limit=limit,
        filters=applied_filters,
        role_keywords=role_keywords,
    )
    ranked_vacancies = _rank_with_domain_boost(stripped_query, role_keywords, vacancies)
    return UserSearchResult(
        user_query=stripped_query,
        role_keywords=role_keywords,
        llm_filters=_serialize_weighted_filters(llm_weighted_filters),
        all_value_counts=_with_all_count_keys(value_counts),
        selected_value_counts=selected_value_counts,
        applied_filters=applied_filters,
        dropped_filters=dropped_filters,
        relax_steps=relax_steps,
        candidate_count=candidate_count,
        vacancies=ranked_vacancies,
    )


def run_user_search(
    user_query: str,
    *,
    limit: int = DEFAULT_SIMILARITY_TOP_K,
    min_candidates: int = DEFAULT_MIN_FILTERED_CANDIDATES,
) -> UserSearchResult:
    """Synchronous wrapper for :func:`user_search` (CLI scripts, REPL)."""
    return asyncio.run(
        user_search(user_query, limit=limit, min_candidates=min_candidates)
    )
