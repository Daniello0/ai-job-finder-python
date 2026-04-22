"""Chat orchestration service for Streamlit app."""

from __future__ import annotations

from dto.chat_dto import ChatMessageDto
from services.backend_api_service import BackendApiService


class ChatService:
    """Build assistant messages from user profile prompts."""

    def __init__(self) -> None:
        self.backend_service = BackendApiService()

    def build_response(self, user_prompt: str) -> ChatMessageDto:
        """Create one assistant message with 0..5 vacancy cards."""
        analyzed = self.backend_service.get_vacancy_for_profile(user_prompt)
        if not analyzed.vacancies:
            return ChatMessageDto(role="assistant", content=analyzed.summary)

        count = len(analyzed.vacancies)
        text = f"{analyzed.summary}\n\nНайдено вакансий: **{count}**."
        return ChatMessageDto(
            role="assistant", content=text, vacancies=analyzed.vacancies
        )
