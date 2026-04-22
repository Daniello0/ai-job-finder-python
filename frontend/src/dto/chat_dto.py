"""DTO models for chat messages in Streamlit state."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel

from dto.vacancy_dto import VacancyDto


class ChatMessageDto(BaseModel):
    """One chat message from user or assistant."""

    role: Literal["user", "assistant"]
    content: str
    vacancies: list[VacancyDto] | None = None
    vacancy: VacancyDto | None = None
