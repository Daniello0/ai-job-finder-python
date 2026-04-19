"""Semantic search over ``vacancies.embedding`` using pgvector cosine distance."""

from __future__ import annotations

import asyncio

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from common.constants.embedding import DEFAULT_SIMILARITY_TOP_K
from features.database.db import async_session_factory
from features.database.models import Vacancy
from features.embedding.encoder import encode_texts, require_pgvector_embedding
from features.embedding.schemas import SimilaritySearchResult


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


async def _search_with_session(
    session: AsyncSession,
    query_vector: list[float],
    *,
    limit: int,
) -> list[SimilaritySearchResult]:
    distance_expr = Vacancy.embedding.cosine_distance(query_vector)
    stmt = (
        select(Vacancy, distance_expr.label("dist"))
        .where(Vacancy.embedding.isnot(None))
        .order_by(distance_expr)
        .limit(limit)
    )
    result = await session.execute(stmt)
    return [_vacancy_to_result(v, d) for v, d in result.all()]


async def similarity_search(
    query_text: str,
    *,
    limit: int = DEFAULT_SIMILARITY_TOP_K,
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

    if session is not None:
        return await _search_with_session(session, query_vector, limit=limit)

    async with async_session_factory() as s:
        return await _search_with_session(s, query_vector, limit=limit)


def run_similarity_search(
    query_text: str,
    *,
    limit: int = DEFAULT_SIMILARITY_TOP_K,
) -> list[SimilaritySearchResult]:
    """Synchronous wrapper for :func:`similarity_search` (scripts, REPL)."""
    return asyncio.run(similarity_search(query_text, limit=limit))
