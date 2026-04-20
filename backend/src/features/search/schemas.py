"""Schemas for orchestration search flow: LLM filters + embedding ranking."""

from __future__ import annotations

from dataclasses import dataclass

from features.embedding.schemas import SimilaritySearchResult


@dataclass(frozen=True, slots=True)
class FilterRelaxStep:
    """One guardrail step where a single filter value is removed."""

    step: int
    filter_key: str
    filter_value: str
    value_count_in_db: int
    candidates_before: int
    candidates_after: int


@dataclass(frozen=True, slots=True)
class UserSearchResult:
    """Final user search output with inferred filters and ranked vacancies."""

    user_query: str
    llm_filters: dict[str, list[str]]
    all_value_counts: dict[str, dict[str, int]]
    selected_value_counts: dict[str, dict[str, int]]
    applied_filters: dict[str, list[str]]
    dropped_filters: dict[str, list[str]]
    relax_steps: list[FilterRelaxStep]
    candidate_count: int
    vacancies: list[SimilaritySearchResult]
