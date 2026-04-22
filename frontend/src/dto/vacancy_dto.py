"""DTO models for vacancy entities returned to UI."""

from __future__ import annotations

from pydantic import BaseModel, HttpUrl


class VacancyDto(BaseModel):
    """Public vacancy payload for the chat UI."""

    id: int
    title: str
    company: str
    salary: str
    payment_frequency: str
    experience: str
    employment: str
    hiring_format: str
    schedule: str
    hours: str
    work_format: str
    skills: str
    url: HttpUrl
    description: str
    cosine_distance: float | None = None
