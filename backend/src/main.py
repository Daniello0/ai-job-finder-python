import asyncio
import json
from dataclasses import asdict
from pathlib import Path

from dotenv import load_dotenv


BACKEND_DIR = Path(__file__).resolve().parents[1]


def fill_database_with_embeddings(
    *,
    batch_size: int | None = None,
    force: bool = False,
) -> int:
    """
    Fill PostgreSQL ``vacancies.embedding`` with Sentence-BERT vectors.

    Call after ``load_dotenv`` so ``DATABASE_URL`` / DB_* are available.

    Uses ``asyncio.run`` (own event loop). Avoid chaining another ``asyncio.run``
    that touches the same global async engine in one process; use a single
    ``asyncio.run`` and ``await fill_db_with_vectors(...)`` instead.
    """
    from common.constants.embedding import DEFAULT_EMBED_BATCH_SIZE
    from features.embedding.save_vectors_service import run_fill_db_with_vectors

    bs = batch_size if batch_size is not None else DEFAULT_EMBED_BATCH_SIZE
    return run_fill_db_with_vectors(batch_size=bs, force=force)


async def _main_async() -> None:
    """Single event loop for parser upsert, embeddings, and search (asyncpg + SQLAlchemy)."""
    load_dotenv(BACKEND_DIR / ".env")

    from common.constants.embedding import DEFAULT_EMBED_BATCH_SIZE
    from features.embedding.save_vectors_service import fill_db_with_vectors
    from features.embedding.similarity_search_service import similarity_search
    from features.parser.file_orchestrator import orchestrate_parser_pipeline_async

    await orchestrate_parser_pipeline_async()

    updated = await fill_db_with_vectors(
        batch_size=DEFAULT_EMBED_BATCH_SIZE, force=False
    )
    print(f"Векторы записаны в БД. Обновлено записей: {updated}")

    results = await similarity_search(
        "Я студент и хочу найти подработку на кассе или в кафе, частичная занятость или гибрид, опыта и образования нет"
    )
    payload = [asdict(r) for r in results]
    print(json.dumps(payload, ensure_ascii=False, indent=2))


def main() -> None:
    asyncio.run(_main_async())


if __name__ == "__main__":
    main()
