import asyncio
import json
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
    from features.parser.file_orchestrator import orchestrate_parser_pipeline_async
    from features.search.service import user_search

    await orchestrate_parser_pipeline_async()

    updated = await fill_db_with_vectors(
        batch_size=DEFAULT_EMBED_BATCH_SIZE, force=False
    )
    print(f"Векторы записаны в БД. Обновлено записей: {updated}")

    print("\nПоиск вакансий. Введите запрос (пустая строка для выхода).")
    while True:
        user_query = input("\nВаш запрос: ").strip()
        if not user_query:
            print("Завершение поиска.")
            break
        try:
            search_result = await user_search(user_query)
        except RuntimeError as error:
            print(f"Поиск недоступен: {error}")
            continue
        print("\nLLM-фильтры:")
        print(json.dumps(search_result.llm_filters, ensure_ascii=False, indent=2))
        print("\nКоличество значений в базе по выбранным фильтрам:")
        print(
            json.dumps(
                search_result.selected_value_counts, ensure_ascii=False, indent=2
            )
        )
        if search_result.relax_steps:
            print("\nШаги ослабления фильтров:")
            for step in search_result.relax_steps:
                print(
                    f"{step.step}. Убрано {step.filter_key}='{step.filter_value}' "
                    f"(в БД: {step.value_count_in_db}) | "
                    f"кандидатов: {step.candidates_before} -> {step.candidates_after}"
                )
        if any(search_result.dropped_filters.values()):
            print("\nОслабленные фильтры (guardrail):")
            print(
                json.dumps(search_result.dropped_filters, ensure_ascii=False, indent=2)
            )
        print(f"\nКандидатов после фильтрации: {search_result.candidate_count}")
        print("Фильтры для поиска:")
        print(json.dumps(search_result.applied_filters, ensure_ascii=False, indent=2))
        if not search_result.vacancies:
            print("Вакансии не найдены по текущим фильтрам.")
            continue
        print("\nТоп вакансий:")
        for index, vacancy in enumerate(search_result.vacancies, start=1):
            print(
                f"{index}. {vacancy.title} — {vacancy.company}\n"
                f"   distance={vacancy.cosine_distance:.4f}\n"
                f"   salary={vacancy.salary}\n"
                f"   experience={vacancy.experience}\n"
                f"   employment={vacancy.employment}\n"
                f"   work_format={vacancy.work_format}\n"
                f"   url={vacancy.url}"
            )


def main() -> None:
    asyncio.run(_main_async())


if __name__ == "__main__":
    main()
