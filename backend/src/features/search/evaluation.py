"""Lightweight offline evaluation for user search quality."""

from __future__ import annotations

import asyncio
from dataclasses import dataclass
from pathlib import Path
import sys

from dotenv import load_dotenv

SRC_DIR = Path(__file__).resolve().parents[2]
BACKEND_DIR = SRC_DIR.parent
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

load_dotenv(BACKEND_DIR / ".env")


@dataclass(frozen=True, slots=True)
class EvalCase:
    """Single benchmark query with expected title keywords."""

    query: str
    expected_keywords: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class EvalReport:
    """Evaluation output for one benchmark query."""

    case: EvalCase
    hit_at_1: bool
    hit_at_5: bool
    error_message: str | None
    top_vacancies: tuple[str, ...]


_EVAL_CASES: tuple[EvalCase, ...] = (
    EvalCase(
        query=(
            "Я студент без опыта, ищу работу в пункте выдачи заказов, "
            "лучше Wildberries или Ozon, формат на месте работодателя."
        ),
        expected_keywords=("пвз", "пункт выдачи", "wildberries", "ozon"),
    ),
    EvalCase(
        query=(
            "Ищу стажировку или junior в интернет-маркетинге, хочу задачи ассистента "
            "маркетолога, желательно с digital-направлением."
        ),
        expected_keywords=("маркетолог", "интернет-маркетолога", "digital"),
    ),
    EvalCase(
        query=(
            "Нужна вакансия бариста или работа в кофейне, можно без опыта, "
            "интересны смены и работа с кофе."
        ),
        expected_keywords=("бариста", "кофе", "кофейн"),
    ),
    EvalCase(
        query=(
            "Ищу работу кладовщиком, желательно 2/2, можно вечерние или ночные "
            "смены, формат строго на месте работодателя."
        ),
        expected_keywords=("кладовщик", "склад"),
    ),
    EvalCase(
        query=(
            "Нужна вакансия комплектовщика или сортировщика на складе, "
            "рассматриваю интенсивный график и ночные смены."
        ),
        expected_keywords=("комплектовщик", "сортировщик", "склад"),
    ),
    EvalCase(
        query=(
            "Ищу работу в логистике: менеджер по логистике, экспедитор или логист, "
            "график 5/2 и понятные задачи."
        ),
        expected_keywords=("логист", "экспедитор"),
    ),
    EvalCase(
        query=(
            "Хочу подработку продавцом в магазине, можно без опыта, "
            "частичная занятость и работа с клиентами."
        ),
        expected_keywords=("продавец",),
    ),
    EvalCase(
        query=(
            "Ищу удаленную работу support/help desk specialist, "
            "где нужно помогать пользователям и решать технические вопросы."
        ),
        expected_keywords=("support", "help desk", "специалист"),
    ),
    EvalCase(
        query=(
            "Ищу вакансию программиста 1C, желательно удаленно, "
            "готов к полной занятости."
        ),
        expected_keywords=("программист 1c", "1c"),
    ),
    EvalCase(
        query=(
            "Интересует работа официантом или поваром, желательно без опыта, "
            "сменный график и работа в команде."
        ),
        expected_keywords=("официант", "повар"),
    ),
    EvalCase(
        query=(
            "Нужна работа водителем с правами категории B, "
            "подойдет разъездной формат и доставка."
        ),
        expected_keywords=("водитель",),
    ),
    EvalCase(
        query=(
            "Ищу стартовую роль в подборе персонала, желательно в IT-сфере, "
            "формат стажировки или junior."
        ),
        expected_keywords=("подбор", "hr", "рекрутер", "персонал"),
    ),
    EvalCase(
        query=(
            "Ищу удаленную вакансию ассистента интернет-маркетолога, "
            "с задачами по контенту и аналитике."
        ),
        expected_keywords=("ассистент интернет-маркетолога", "маркетолог"),
    ),
    EvalCase(
        query=(
            "Хочу работу мерчендайзером или торговым представителем, "
            "с разъездным характером и коммуникацией с клиентами."
        ),
        expected_keywords=("мерчендайзер", "торгов"),
    ),
    EvalCase(
        query=(
            "Нужна вакансия кондитера или помощника кондитера, "
            "интересны сменные графики и работа с десертами."
        ),
        expected_keywords=("кондитер", "десерт"),
    ),
    EvalCase(
        query=(
            "Ищу работу в ПВЗ Ozon или Wildberries, где нужно выдавать посылки, "
            "общаться с клиентами и вести прием заказов."
        ),
        expected_keywords=("пвз", "ozon", "wildberries", "пункт выдачи"),
    ),
)


def _text_hit(text: str, expected_keywords: tuple[str, ...]) -> bool:
    haystack = text.lower()
    return any(keyword in haystack for keyword in expected_keywords)


def _format_vacancy(index: int, item: object) -> str:
    return (
        f"{index}. id={item.id} | title={item.title} | company={item.company}\n"
        f"   salary={item.salary}\n"
        f"   payment_frequency={item.payment_frequency}\n"
        f"   experience={item.experience}\n"
        f"   employment={item.employment}\n"
        f"   hiring_format={item.hiring_format}\n"
        f"   schedule={item.schedule}\n"
        f"   hours={item.hours}\n"
        f"   work_format={item.work_format}\n"
        f"   cosine_distance={item.cosine_distance:.4f}\n"
        f"   url={item.url}"
    )


async def _case_hits(case: EvalCase) -> EvalReport:
    from features.search.service import user_search

    try:
        result = await user_search(case.query)
    except RuntimeError as error:
        return EvalReport(
            case=case,
            hit_at_1=False,
            hit_at_5=False,
            error_message=str(error),
            top_vacancies=(),
        )
    if not result.vacancies:
        return EvalReport(
            case=case,
            hit_at_1=False,
            hit_at_5=False,
            error_message=None,
            top_vacancies=(),
        )
    top_1 = result.vacancies[0]
    top_1_text = f"{top_1.title} {top_1.skills}"
    hit_at_1 = _text_hit(top_1_text, case.expected_keywords)
    top_5_text = (f"{item.title} {item.skills}" for item in result.vacancies[:5])
    hit_at_5 = any(_text_hit(text, case.expected_keywords) for text in top_5_text)
    top_vacancies = tuple(
        _format_vacancy(index, item)
        for index, item in enumerate(result.vacancies[:5], start=1)
    )
    return EvalReport(
        case=case,
        hit_at_1=hit_at_1,
        hit_at_5=hit_at_5,
        error_message=None,
        top_vacancies=top_vacancies,
    )


async def _run_search_evaluation_async() -> None:
    """Run benchmark queries and print hit@1 / hit@5."""
    from features.database.db import engine

    hits_1 = 0
    hits_5 = 0
    for index, case in enumerate(_EVAL_CASES, start=1):
        report = await _case_hits(case)
        hits_1 += int(report.hit_at_1)
        hits_5 += int(report.hit_at_5)
        print(f"\n[{index}] Query: {report.case.query}")
        print(f"Expected keywords: {', '.join(report.case.expected_keywords)}")
        print(f"hit@1={report.hit_at_1} hit@5={report.hit_at_5}")
        if report.error_message:
            print(f"Case error: {report.error_message}")
            continue
        if not report.top_vacancies:
            print("Top vacancies: none")
            continue
        print("Top vacancies:")
        for line in report.top_vacancies:
            print(line)
    total = len(_EVAL_CASES)
    print(f"\nSummary: hit@1={hits_1}/{total}, hit@5={hits_5}/{total}")
    await engine.dispose()


def run_search_evaluation() -> None:
    """Run evaluation in a single asyncio event loop."""
    asyncio.run(_run_search_evaluation_async())


if __name__ == "__main__":
    run_search_evaluation()
