"""Compute and persist vacancy embeddings (title + skills + description)."""

from __future__ import annotations

import asyncio
from typing import Any

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from common.constants.embedding import (
    DEFAULT_EMBED_BATCH_SIZE,
    EMBEDDING_MODEL_NAME,
)
from features.database.db import async_session_factory
from features.database.models import Vacancy, Vector

_model: Any = None


def _require_pgvector_embedding() -> None:
    """Ensure ORM was built with pgvector (Vector column), not Text fallback."""
    if Vector is None:
        msg = (
            "pgvector is required: install pgvector and use PostgreSQL for embeddings."
        )
        raise RuntimeError(msg)


def _vacancy_embed_text(title: str, skills: str, description: str) -> str:
    parts = [title.strip(), skills.strip(), description.strip()]
    return "\n\n".join(p for p in parts if p)


def _torch_major_minor(version: str) -> tuple[int, int]:
    core = version.split("+", 1)[0].strip().split(".")[:2]
    return int(core[0]), int(core[1])


def _require_torch_for_embeddings() -> None:
    """sentence-transformers needs a working PyTorch 2.x (see backend/requirements.txt pins)."""
    try:
        import torch
    except ModuleNotFoundError as err:
        msg = "Install PyTorch 2.x: `pip install torch` (see backend/requirements.txt)."
        raise RuntimeError(msg) from err
    if _torch_major_minor(torch.__version__) < (2, 0):
        msg = f"PyTorch 2.x is required for Sentence-BERT (found {torch.__version__})."
        raise RuntimeError(msg)


def _get_sentence_transformer() -> Any:
    global _model
    if _model is None:
        _require_torch_for_embeddings()
        try:
            from sentence_transformers import SentenceTransformer
        except ModuleNotFoundError as err:
            msg = (
                "Install sentence-transformers in this Python environment, e.g. "
                "`pip install sentence-transformers` or `pip install -r backend/requirements.txt`."
            )
            raise RuntimeError(msg) from err

        _model = SentenceTransformer(EMBEDDING_MODEL_NAME)
    return _model


async def _encode_texts(texts: list[str]) -> list[list[float]]:
    """Run Sentence-BERT encoding off the asyncio event loop."""

    def _encode() -> Any:
        st = _get_sentence_transformer()
        return st.encode(
            texts,
            batch_size=min(len(texts), DEFAULT_EMBED_BATCH_SIZE),
            show_progress_bar=False,
        )

    arr = await asyncio.to_thread(_encode)
    return [arr[i].tolist() for i in range(len(texts))]


async def _fetch_batch(
    session: AsyncSession,
    *,
    after_id: int,
    batch_size: int,
    force: bool,
) -> list[Any]:
    stmt = (
        select(Vacancy.id, Vacancy.title, Vacancy.skills, Vacancy.description)
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
    texts = [_vacancy_embed_text(r.title, r.skills, r.description) for r in rows]
    vectors = await _encode_texts(texts)
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

    By default updates only rows with ``embedding IS NULL``. Set ``force=True`` to
    recompute embeddings for every vacancy (keyset pagination by ``id``).

    Returns the number of rows updated.
    """
    _require_pgvector_embedding()
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
