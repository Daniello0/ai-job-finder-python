"""Structured results for embedding-powered vacancy search."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class SimilaritySearchResult:
    """
    One vacancy from PostgreSQL ranked by pgvector cosine distance to the query vector.

    ``cosine_distance`` is the ``<=>`` operator value (lower means more similar).
    """

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
    url: str
    description: str
    cosine_distance: float
