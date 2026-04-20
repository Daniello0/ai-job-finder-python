"""Semantic search over ``vacancies.embedding`` using pgvector cosine distance."""

from __future__ import annotations

import asyncio

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from common.constants.embedding import DEFAULT_SIMILARITY_TOP_K
from common.constants.llm import VACANCY_FILTER_KEYS
from features.database.db import async_session_factory
from features.database.models import Vacancy
from features.embedding.encoder import encode_texts, require_pgvector_embedding
from features.embedding.schemas import SimilaritySearchResult

_FILTER_COLUMN_MAP = {
    "payment_frequency": Vacancy.payment_frequency,
    "experience": Vacancy.experience,
    "employment": Vacancy.employment,
    "hiring_format": Vacancy.hiring_format,
    "schedule": Vacancy.schedule,
    "hours": Vacancy.hours,
    "work_format": Vacancy.work_format,
}


def _vacancy_to_result(row: Vacancy, distance: float) -> SimilaritySearchResult:
    return SimilaritySearchResult(
        id=row.id,
        title=row.title,
        company=row.company,
        salary=row.salary,
        payment_frequency=row.payment_frequency,
        experience=row.experience,
        employment=row.employment,
        hiring_format=row.hiring_format,
        schedule=row.schedule,
        hours=row.hours,
        work_format=row.work_format,
        skills=row.skills,
        url=row.url,
        description=row.description,
        cosine_distance=float(distance),
    )


def _normalize_filters(
    filters: dict[str, list[str]] | None,
) -> dict[str, list[str]]:
    if not filters:
        return {}
    unknown = sorted(set(filters) - set(VACANCY_FILTER_KEYS))
    if unknown:
        msg = f"Unknown filter keys: {', '.join(unknown)}."
        raise ValueError(msg)
    normalized: dict[str, list[str]] = {}
    for key in VACANCY_FILTER_KEYS:
        values = filters.get(key, [])
        cleaned = sorted({item.strip() for item in values if item.strip()})
        if cleaned:
            normalized[key] = cleaned
    return normalized


def _apply_filters(
    stmt: object,
    filters: dict[str, list[str]],
):
    for key, values in filters.items():
        stmt = stmt.where(_FILTER_COLUMN_MAP[key].in_(values))
    return stmt


async def _search_with_session(
    session: AsyncSession,
    query_vector: list[float],
    *,
    limit: int,
    filters: dict[str, list[str]],
) -> list[SimilaritySearchResult]:
    distance_expr = Vacancy.embedding.cosine_distance(query_vector)
    stmt = (
        select(Vacancy, distance_expr.label("dist"))
        .where(Vacancy.embedding.isnot(None))
        .order_by(distance_expr)
        .limit(limit)
    )
    stmt = _apply_filters(stmt, filters)
    result = await session.execute(stmt)
    return [_vacancy_to_result(v, d) for v, d in result.all()]


async def similarity_search(
    query_text: str,
    *,
    limit: int = DEFAULT_SIMILARITY_TOP_K,
    filters: dict[str, list[str]] | None = None,
    session: AsyncSession | None = None,
) -> list[SimilaritySearchResult]:
    """
    Vectorize ``query_text`` and return vacancies ordered by cosine distance (closest first).

    Uses the same Sentence-BERT model and dimension (384) as :mod:`save_vectors_service`.
    """
    require_pgvector_embedding()
    stripped = query_text.strip()
    if not stripped:
        return []

    vectors = await encode_texts([stripped])
    query_vector = vectors[0]
    normalized_filters = _normalize_filters(filters)

    if session is not None:
        return await _search_with_session(
            session, query_vector, limit=limit, filters=normalized_filters
        )

    async with async_session_factory() as s:
        return await _search_with_session(
            s, query_vector, limit=limit, filters=normalized_filters
        )


def run_similarity_search(
    query_text: str,
    *,
    limit: int = DEFAULT_SIMILARITY_TOP_K,
    filters: dict[str, list[str]] | None = None,
) -> list[SimilaritySearchResult]:
    """Synchronous wrapper for :func:`similarity_search` (scripts, REPL)."""
    return asyncio.run(similarity_search(query_text, limit=limit, filters=filters))
