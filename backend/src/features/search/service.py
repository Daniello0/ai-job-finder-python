"""Orchestrate user search: LLM filter extraction then filtered embedding search."""

from __future__ import annotations

import asyncio
from collections import deque
from typing import Any

from common.constants.embedding import DEFAULT_SIMILARITY_TOP_K
from common.constants.llm import VACANCY_FILTER_KEYS
from common.constants.search import DEFAULT_MIN_FILTERED_CANDIDATES
from sqlalchemy import Select, func, select

from features.database.db import async_session_factory
from features.database.models import Vacancy
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


def _empty_filters() -> dict[str, list[str]]:
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


def _normalize_filters(payload: dict[str, Any]) -> dict[str, list[str]]:
    normalized = _empty_filters()
    for key in VACANCY_FILTER_KEYS:
        value = payload.get(key, [])
        if not isinstance(value, list):
            msg = f"Filter '{key}' must be a list of strings."
            raise ValueError(msg)
        cleaned = sorted(
            {item.strip() for item in value if isinstance(item, str) and item.strip()}
        )
        normalized[key] = cleaned
    return normalized


def _apply_filters(
    stmt: Select[tuple[int]], filters: dict[str, list[str]]
) -> Select[tuple[int]]:
    for key, values in filters.items():
        if values:
            stmt = stmt.where(_FILTER_COLUMN_MAP[key].in_(values))
    return stmt


async def _count_filtered_candidates(filters: dict[str, list[str]]) -> int:
    stmt = select(func.count(Vacancy.id))
    stmt = _apply_filters(stmt, filters)
    async with async_session_factory() as session:
        count = await session.scalar(stmt)
    return int(count or 0)


def _drop_filter_value(filters: dict[str, list[str]], key: str, value: str) -> None:
    updated = [item for item in filters.get(key, []) if item != value]
    if updated:
        filters[key] = updated
    else:
        filters.pop(key, None)


def _build_selected_value_counts(
    filters: dict[str, list[str]],
    value_counts: dict[str, dict[str, int]],
) -> dict[str, dict[str, int]]:
    selected_counts = _empty_filter_counts()
    for key in VACANCY_FILTER_KEYS:
        for value in filters.get(key, []):
            selected_counts[key][value] = value_counts.get(key, {}).get(value, 0)
    return selected_counts


def _flatten_selected_filters(filters: dict[str, list[str]]) -> list[tuple[str, str]]:
    selected: list[tuple[str, str]] = []
    for key in VACANCY_FILTER_KEYS:
        for value in filters.get(key, []):
            selected.append((key, value))
    return selected


def _build_filters_from_removed_state(
    base_filters: dict[str, list[str]],
    selected_filters: list[tuple[str, str]],
    removed_state: frozenset[int],
) -> dict[str, list[str]]:
    active_filters = _clone_non_empty(base_filters)
    for index in removed_state:
        key, value = selected_filters[index]
        _drop_filter_value(active_filters, key, value)
    return active_filters


def _choose_best_feasible_state(
    feasible_states: list[tuple[frozenset[int], int]],
    selected_filters: list[tuple[str, str]],
) -> tuple[frozenset[int], int]:
    def _state_signature(state: frozenset[int]) -> tuple[str, ...]:
        return tuple(
            f"{selected_filters[i][0]}::{selected_filters[i][1]}" for i in sorted(state)
        )

    max_count = max(count for _, count in feasible_states)
    candidates = [
        (state, count) for state, count in feasible_states if count == max_count
    ]
    return min(candidates, key=lambda item: _state_signature(item[0]))


def _build_relax_steps(
    final_state: frozenset[int],
    *,
    parent: dict[frozenset[int], tuple[frozenset[int], int]],
    state_counts: dict[frozenset[int], int],
    selected_filters: list[tuple[str, str]],
    value_counts: dict[str, dict[str, int]],
) -> tuple[dict[str, list[str]], list[FilterRelaxStep]]:
    dropped_filters = _empty_filters()
    steps_with_states: list[tuple[frozenset[int], frozenset[int], int]] = []
    state = final_state
    while state in parent:
        prev_state, removed_index = parent[state]
        steps_with_states.append((prev_state, state, removed_index))
        state = prev_state
    steps_with_states.reverse()

    relax_steps: list[FilterRelaxStep] = []
    for step_index, (before_state, after_state, removed_index) in enumerate(
        steps_with_states, start=1
    ):
        key, value = selected_filters[removed_index]
        dropped_filters[key].append(value)
        relax_steps.append(
            FilterRelaxStep(
                step=step_index,
                filter_key=key,
                filter_value=value,
                value_count_in_db=value_counts.get(key, {}).get(value, 0),
                candidates_before=state_counts[before_state],
                candidates_after=state_counts[after_state],
            )
        )
    return dropped_filters, relax_steps


async def _relax_filters(
    llm_filters: dict[str, list[str]],
    *,
    value_counts: dict[str, dict[str, int]],
    min_candidates: int,
) -> tuple[dict[str, list[str]], dict[str, list[str]], list[FilterRelaxStep], int]:
    selected_filters = _flatten_selected_filters(llm_filters)
    initial_state: frozenset[int] = frozenset()
    state_counts: dict[frozenset[int], int] = {}

    async def _count_state(removed_state: frozenset[int]) -> int:
        if removed_state in state_counts:
            return state_counts[removed_state]
        active_filters = _build_filters_from_removed_state(
            llm_filters, selected_filters, removed_state
        )
        count = await _count_filtered_candidates(active_filters)
        state_counts[removed_state] = count
        return count

    best_state = initial_state
    best_count = await _count_state(initial_state)
    if best_count >= min_candidates:
        return (
            _with_all_keys(_clone_non_empty(llm_filters)),
            _empty_filters(),
            [],
            best_count,
        )

    queue: deque[frozenset[int]] = deque([initial_state])
    visited: set[frozenset[int]] = {initial_state}
    parent: dict[frozenset[int], tuple[frozenset[int], int]] = {}
    while queue:
        level_size = len(queue)
        feasible_states: list[tuple[frozenset[int], int]] = []
        for _ in range(level_size):
            state = queue.popleft()
            candidate_count = await _count_state(state)
            if candidate_count > best_count:
                best_state = state
                best_count = candidate_count
            if candidate_count >= min_candidates:
                feasible_states.append((state, candidate_count))
                continue
            for removed_index in range(len(selected_filters)):
                if removed_index in state:
                    continue
                next_state = state | {removed_index}
                if next_state in visited:
                    continue
                visited.add(next_state)
                parent[next_state] = (state, removed_index)
                queue.append(next_state)
        if feasible_states:
            best_state, best_count = _choose_best_feasible_state(
                feasible_states, selected_filters
            )
            break

    active_filters = _build_filters_from_removed_state(
        llm_filters, selected_filters, best_state
    )
    dropped_filters, relax_steps = _build_relax_steps(
        best_state,
        parent=parent,
        state_counts=state_counts,
        selected_filters=selected_filters,
        value_counts=value_counts,
    )
    return _with_all_keys(active_filters), dropped_filters, relax_steps, best_count


async def user_search(
    user_query: str,
    *,
    limit: int = DEFAULT_SIMILARITY_TOP_K,
    min_candidates: int = DEFAULT_MIN_FILTERED_CANDIDATES,
) -> UserSearchResult:
    """
    Run user-facing search flow:
    1) infer structured filters via LLM,
    2) relax rare filters until enough candidates,
    3) run embedding similarity search within filtered vacancy subset.
    """
    stripped_query = user_query.strip()
    if not stripped_query:
        return UserSearchResult(
            user_query="",
            llm_filters=_empty_filters(),
            all_value_counts=_empty_filter_counts(),
            selected_value_counts=_empty_filter_counts(),
            applied_filters=_empty_filters(),
            dropped_filters=_empty_filters(),
            relax_steps=[],
            candidate_count=0,
            vacancies=[],
        )
    raw_filters = await get_vacancy_filters_from_text_async(stripped_query)
    llm_filters = _normalize_filters(raw_filters)
    value_counts = await build_vacancy_filter_value_counts()
    selected_value_counts = _build_selected_value_counts(llm_filters, value_counts)
    (
        applied_filters,
        dropped_filters,
        relax_steps,
        candidate_count,
    ) = await _relax_filters(
        llm_filters,
        value_counts=value_counts,
        min_candidates=min_candidates,
    )
    vacancies = await similarity_search(
        stripped_query,
        limit=limit,
        filters=applied_filters,
    )
    return UserSearchResult(
        user_query=stripped_query,
        llm_filters=llm_filters,
        all_value_counts=_with_all_count_keys(value_counts),
        selected_value_counts=selected_value_counts,
        applied_filters=applied_filters,
        dropped_filters=dropped_filters,
        relax_steps=relax_steps,
        candidate_count=candidate_count,
        vacancies=vacancies,
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
