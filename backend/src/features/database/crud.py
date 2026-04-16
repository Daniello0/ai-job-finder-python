from __future__ import annotations

from typing import Any

from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.dialects.postgresql import Insert

from features.database.models import Vacancy


VACANCY_INPUT_FIELDS: tuple[str, ...] = (
    "title",
    "company",
    "salary",
    "payment_frequency",
    "experience",
    "employment",
    "hiring_format",
    "schedule",
    "hours",
    "work_format",
    "skills",
    "url",
    "description",
)


def _as_rows(cleaned_data: Any) -> list[dict[str, Any]]:
    if cleaned_data is None:
        return []

    if isinstance(cleaned_data, list):
        return [dict(row) for row in cleaned_data]

    to_dict = getattr(cleaned_data, "to_dict", None)
    if callable(to_dict):
        # pandas.DataFrame -> list[dict]
        return cleaned_data.to_dict(orient="records")  # type: ignore[no-any-return]

    raise TypeError(f"Unsupported cleaned_data type: {type(cleaned_data)!r}")


def _normalize_vacancy_payload(row: dict[str, Any]) -> dict[str, Any]:
    payload: dict[str, Any] = {}
    for field in VACANCY_INPUT_FIELDS:
        value = row.get(field, "")
        payload[field] = "" if value is None else str(value)
    return payload


def _build_upsert(values: list[dict[str, Any]]) -> Insert:
    stmt = insert(Vacancy).values(values)
    update_cols = {col: getattr(stmt.excluded, col) for col in VACANCY_INPUT_FIELDS if col != "url"}
    return stmt.on_conflict_do_update(
        index_elements=[Vacancy.url],
        set_=update_cols,
    )


async def upsert_vacancies(session: AsyncSession, cleaned_data: Any) -> int:
    """Upsert parsed vacancies into PostgreSQL and return affected rows count."""

    rows = _as_rows(cleaned_data)
    values = [_normalize_vacancy_payload(row) for row in rows if row.get("url")]
    if not values:
        return 0

    stmt = _build_upsert(values)
    result = await session.execute(stmt)
    await session.commit()
    return int(result.rowcount or 0)

