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
    from features.llm.service import get_vacancy_filters_from_text_async
    from features.parser.file_orchestrator import orchestrate_parser_pipeline_async

    await orchestrate_parser_pipeline_async()

    updated = await fill_db_with_vectors(
        batch_size=DEFAULT_EMBED_BATCH_SIZE, force=False
    )
    print(f"Векторы записаны в БД. Обновлено записей: {updated}")

    # results = await similarity_search(
    #     "Я студент и хочу найти подработку на кассе или в кафе, частичная занятость или гибрид, опыта и образования нет"
    # )
    # payload = [asdict(r) for r in results]
    # print(json.dumps(payload, ensure_ascii=False, indent=2))

    test_queries = [
        "Я студент, хочу работать бариста и варить кофе, или поваром делать десерты, "
        "не полный рабочий день и без опыта",

        "Ищу работу мерчендайзером или торговым представителем с опытом 1-3 года, "
        "нужны вечерние или ночные смены, формат разъездной, трудоустройство по ГПХ. "
        "Навыки: активные продажи, работа с клиентами, права категории B",

        "Я – студент, ищу работу программистом, опыта нет, образование – незаконченное высшее, "
        "хочу найти с неполным рабочим графиком, можно удаленно или гибрид",

        "Ищу подработку без опыта, выплаты раз в неделю или ежедневно, график по выходным или свободный, "
        "можно 4-6 часов в день, формат на месте работодателя."
    ]
    for index, user_query in enumerate(test_queries, start=1):
        try:
            llm_filters = await get_vacancy_filters_from_text_async(user_query)
            print(f"LLM test #{index}:")
            print(json.dumps(llm_filters, ensure_ascii=False, indent=2))
        except RuntimeError as error:
            print(f"LLM test #{index} unavailable: {error}")


def main() -> None:
    asyncio.run(_main_async())


if __name__ == "__main__":
    main()
