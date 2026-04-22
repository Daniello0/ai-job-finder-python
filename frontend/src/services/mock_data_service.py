"""Mock provider used before backend API routes are available."""

from __future__ import annotations

from dto.vacancy_dto import VacancyDto


def get_mock_vacancy() -> VacancyDto:
    """Return one demo vacancy for frontend visual validation."""
    return VacancyDto(
        id=101,
        title="Junior Python Developer",
        company="BelTech Solutions",
        salary="2000-2800 BYN",
        payment_frequency="Два раза в месяц",
        experience="От 6 месяцев",
        employment="Полная занятость",
        hiring_format="Стандартный найм",
        schedule="Пн-Пт",
        hours="40 часов в неделю",
        work_format="Гибрид, Минск",
        skills="Python, FastAPI, PostgreSQL, Docker, Git",
        url="https://rabota.by/vacancy/123456",
        description=(
            "Ищем Junior Python Developer в команду продуктовой разработки. "
            "Вы будете участвовать в создании микросервисов на FastAPI, "
            "интеграциях с внешними API и оптимизации SQL-запросов. "
            "Важно базовое понимание асинхронности, тестирования и контейнеризации. "
            "Предусмотрено менторство, ревью кода и понятный план роста на 6 месяцев. "
            "Плюсом будет опыт pet-проектов и участие в хакатонах."
        ),
        cosine_distance=0.1723,
    )
