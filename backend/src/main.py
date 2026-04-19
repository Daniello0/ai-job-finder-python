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
    """
    from common.constants.embedding import DEFAULT_EMBED_BATCH_SIZE
    from features.embedding.service import run_fill_db_with_vectors

    bs = batch_size if batch_size is not None else DEFAULT_EMBED_BATCH_SIZE
    return run_fill_db_with_vectors(batch_size=bs, force=force)


def main() -> None:
    """Load environment variables and run the embedding pipeline."""
    load_dotenv(BACKEND_DIR / ".env")

    updated = fill_database_with_embeddings()
    print(f"Векторы записаны в БД. Обновлено записей: {updated}")


if __name__ == "__main__":
    main()
