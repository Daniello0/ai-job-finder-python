from __future__ import annotations

from sqlalchemy import String, Text, UniqueConstraint
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


try:
    from pgvector.sqlalchemy import Vector
except ModuleNotFoundError:  # pragma: no cover
    Vector = None  # type: ignore[assignment]


class Base(DeclarativeBase):
    """Base class for ORM models."""


class Vacancy(Base):
    """Vacancy ORM model used for ingestion and semantic search."""

    __tablename__ = "vacancies"
    __table_args__ = (UniqueConstraint("url", name="uq_vacancies_url"),)

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)

    title: Mapped[str] = mapped_column(String(512), nullable=False)
    company: Mapped[str] = mapped_column(String(512), nullable=False)
    salary: Mapped[str] = mapped_column(String(256), nullable=False)
    payment_frequency: Mapped[str] = mapped_column(String(128), nullable=False)
    experience: Mapped[str] = mapped_column(String(256), nullable=False)
    employment: Mapped[str] = mapped_column(String(256), nullable=False)
    hiring_format: Mapped[str] = mapped_column(String(256), nullable=False)
    schedule: Mapped[str] = mapped_column(String(256), nullable=False)
    hours: Mapped[str] = mapped_column(String(256), nullable=False)
    work_format: Mapped[str] = mapped_column(String(256), nullable=False)

    skills: Mapped[str] = mapped_column(Text, nullable=False)
    url: Mapped[str] = mapped_column(String(2048), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)

    if Vector is not None:
        embedding: Mapped[list[float] | None] = mapped_column(
            Vector(384), nullable=True
        )
    else:
        embedding: Mapped[str | None] = mapped_column(Text, nullable=True)
