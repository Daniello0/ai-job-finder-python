"""Chat orchestration service for Streamlit app."""

from __future__ import annotations

from dto.chat_dto import ChatMessageDto
from dto.vacancy_dto import VacancyDto
from services.backend_api_service import BackendApiService


class ChatService:
    """Build assistant messages from user profile prompts."""

    def __init__(self) -> None:
        self.backend_service = BackendApiService()

    @staticmethod
    def _sort_vacancies_by_similarity(vacancies: list[VacancyDto]) -> list[VacancyDto]:
        """Sort vacancies so the smallest cosine distance appears first."""
        return sorted(
            vacancies,
            key=lambda vacancy: (
                vacancy.cosine_distance is None,
                vacancy.cosine_distance if vacancy.cosine_distance is not None else float("inf"),
            ),
        )

    def build_response(self, user_prompt: str) -> ChatMessageDto:
        """Create one assistant message with 0..5 vacancy cards."""
        analyzed = self.backend_service.get_vacancy_for_profile(user_prompt)
        if not analyzed.vacancies:
            return ChatMessageDto(role="assistant", content=analyzed.summary)

        sorted_vacancies = self._sort_vacancies_by_similarity(analyzed.vacancies)
        count = len(sorted_vacancies)
        text = f"{analyzed.summary}\n\nНайдено вакансий: **{count}**."
        return ChatMessageDto(
            role="assistant", content=text, vacancies=sorted_vacancies
        )
