"""Schemas for OpenRouter LLM interactions."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True, slots=True)
class LlmAnswer:
    """Parsed LLM response with JSON payload and metadata."""

    model: str
    raw_content: str
    payload: dict[str, Any]
