"""Compute and persist vacancy embeddings (weighted structured fields; description optional)."""

from __future__ import annotations

import asyncio
from typing import Any

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from common.constants.embedding import (
    DEFAULT_EMBED_BATCH_SIZE,
    VACANCY_EMBED_COMPANY_REPEATS,
    VACANCY_EMBED_DESCRIPTION_MAX_CHARS,
    VACANCY_EMBED_INCLUDE_DESCRIPTION,
    VACANCY_EMBED_SKILLS_REPEATS,
    VACANCY_EMBED_STRUCTURE_REPEATS,
    VACANCY_EMBED_TITLE_REPEATS,
)
from features.database.db import async_session_factory
from features.database.models import Vacancy
from features.embedding.encoder import encode_texts, require_pgvector_embedding

_SKIP_PLACEHOLDERS: frozenset[str] = frozenset(
    {"", "не указано", "не указаны", "-"},
)

_STRUCTURE_FIELDS: tuple[tuple[str, str], ...] = (
    ("Занятость", "employment"),
    ("График", "schedule"),
    ("Часы", "hours"),
    ("Формат работы", "work_format"),
    ("Опыт", "experience"),
    ("Трудоустройство", "hiring_format"),
)


def _trim(s: str) -> str:
    return s.strip()


def _skip_value(value: str) -> bool:
    t = _trim(value).lower()
    return not t or t in _SKIP_PLACEHOLDERS


def _repeat_lines(label: str, value: str, times: int) -> list[str]:
    if _skip_value(value):
        return []
    line = f"{label}: {_trim(value)}"
    return [line] * times


def _description_for_embed(raw: str) -> str | None:
    """Return description slice for embedding, or None if disabled / empty."""
    if not VACANCY_EMBED_INCLUDE_DESCRIPTION:
        return None
    t = _trim(raw)
    if not t:
        return None
    cap = VACANCY_EMBED_DESCRIPTION_MAX_CHARS
    if cap is not None and len(t) > cap:
        return t[:cap].rstrip() + "…"
    return t


def _vacancy_embed_text(row: Any) -> str:
    """
    Build one string for embedding: title and structured fields (weighted by repetition),
    then skills. Description is optional (see ``VACANCY_EMBED_INCLUDE_DESCRIPTION``).
    """
    chunks: list[str] = []

    title = _trim(row.title)
    if title:
        job_line = f"Должность: {title}"
        chunks.extend([job_line] * VACANCY_EMBED_TITLE_REPEATS)

    chunks.extend(_repeat_lines("Компания", row.company, VACANCY_EMBED_COMPANY_REPEATS))
    for label, attr in _STRUCTURE_FIELDS:
        chunks.extend(
            _repeat_lines(
                label,
                getattr(row, attr),
                VACANCY_EMBED_STRUCTURE_REPEATS,
            )
        )
    chunks.extend(_repeat_lines("Зарплата", row.salary, 1))
    chunks.extend(_repeat_lines("Выплаты", row.payment_frequency, 1))

    if not _skip_value(row.skills):
        sk = f"Навыки: {_trim(row.skills)}"
        chunks.extend([sk] * VACANCY_EMBED_SKILLS_REPEATS)

    desc = _description_for_embed(row.description)
    if desc:
        chunks.append(f"Описание: {desc}")

    return "\n\n".join(chunks)


async def _fetch_batch(
    session: AsyncSession,
    *,
    after_id: int,
    batch_size: int,
    force: bool,
) -> list[Any]:
    stmt = (
        select(
            Vacancy.id,
            Vacancy.title,
            Vacancy.company,
            Vacancy.salary,
            Vacancy.payment_frequency,
            Vacancy.experience,
            Vacancy.employment,
            Vacancy.hiring_format,
            Vacancy.schedule,
            Vacancy.hours,
            Vacancy.work_format,
            Vacancy.skills,
            Vacancy.description,
        )
        .where(Vacancy.id > after_id)
        .order_by(Vacancy.id)
        .limit(batch_size)
    )
    if not force:
        stmt = stmt.where(Vacancy.embedding.is_(None))
    result = await session.execute(stmt)
    return list(result.all())


async def _persist_vectors(
    session: AsyncSession,
    ids: list[int],
    vectors: list[list[float]],
) -> None:
    for vid, vec in zip(ids, vectors, strict=True):
        await session.execute(
            update(Vacancy).where(Vacancy.id == vid).values(embedding=vec)
        )
    await session.commit()


async def _embed_and_store_batch(
    session: AsyncSession,
    rows: list[Any],
) -> int:
    texts = [_vacancy_embed_text(r) for r in rows]
    vectors = await encode_texts(texts)
    ids = [r.id for r in rows]
    await _persist_vectors(session, ids, vectors)
    return len(ids)


async def fill_db_with_vectors(
    *,
    batch_size: int = DEFAULT_EMBED_BATCH_SIZE,
    force: bool = False,
) -> int:
    """
    Fill ``vacancies.embedding`` using Sentence-BERT (multilingual MiniLM, dim 384).

    Text combines weighted structured fields (title, schedule, employment, …), skills,
    and optionally the full description (see ``VACANCY_EMBED_INCLUDE_DESCRIPTION``). After
    changing embedding settings in ``common.constants.embedding``, run with ``force=True``
    to refresh all vectors.

    By default updates only rows with ``embedding IS NULL``. Set ``force=True`` to
    recompute embeddings for every vacancy (keyset pagination by ``id``).

    Returns the number of rows updated.
    """
    require_pgvector_embedding()
    total = 0
    after_id = 0
    async with async_session_factory() as session:
        while True:
            rows = await _fetch_batch(
                session,
                after_id=after_id,
                batch_size=batch_size,
                force=force,
            )
            if not rows:
                break
            after_id = rows[-1].id
            total += await _embed_and_store_batch(session, rows)
    return total


def run_fill_db_with_vectors(
    *,
    batch_size: int = DEFAULT_EMBED_BATCH_SIZE,
    force: bool = False,
) -> int:
    """
    Run :func:`fill_db_with_vectors` from synchronous code (CLI, scripts).

    Wraps ``asyncio.run`` so callers do not need to manage an event loop.
    """
    return asyncio.run(fill_db_with_vectors(batch_size=batch_size, force=force))
