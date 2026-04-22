"""Chat orchestration service for Streamlit app."""

from __future__ import annotations

from dto.chat_dto import ChatMessageDto
from services.backend_api_service import BackendApiService


class ChatService:
    """Build assistant messages from user profile prompts."""

    def __init__(self) -> None:
        self.backend_service = BackendApiService()

    def build_response(self, user_prompt: str) -> ChatMessageDto:
        """Create one assistant message with vacancy card."""
        analyzed = self.backend_service.get_vacancy_for_profile(user_prompt)
        best_match = analyzed.vacancies[0]
        text = (
            f"{analyzed.summary}\n\n"
            f"Нашел подходящий вариант: **{best_match.title}** в **{best_match.company}**."
        )
        return ChatMessageDto(role="assistant", content=text, vacancy=best_match)
