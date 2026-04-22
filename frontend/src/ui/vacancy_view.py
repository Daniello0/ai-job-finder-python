"""UI components for vacancy rendering."""

from __future__ import annotations

import streamlit as st

from constants.ui import DESCRIPTION_PREVIEW_LENGTH
from dto.vacancy_dto import VacancyDto


def _build_description(vacancy: VacancyDto, expanded: bool) -> str:
    """Return full or shortened description based on toggle state."""
    if expanded or len(vacancy.description) <= DESCRIPTION_PREVIEW_LENGTH:
        return vacancy.description
    preview = vacancy.description[:DESCRIPTION_PREVIEW_LENGTH].rstrip()
    return f"{preview}..."


def _toggle_description(vacancy_id: int) -> None:
    """Flip expanded state for one vacancy."""
    key = f"vacancy_description_{vacancy_id}"
    current = st.session_state.vacancy_expanded.get(key, False)
    st.session_state.vacancy_expanded[key] = not current


def render_vacancy_card(vacancy: VacancyDto) -> None:
    """Render vacancy details with description show more/hide."""
    key = f"vacancy_description_{vacancy.id}"
    expanded = st.session_state.vacancy_expanded.get(key, False)

    st.markdown("### Вакансия")
    st.markdown(f"**{vacancy.title}**")
    st.markdown(f"Компания: **{vacancy.company}**")
    st.markdown(f"Зарплата: `{vacancy.salary}`")
    st.markdown(f"Формат работы: `{vacancy.work_format}`")
    st.markdown(f"Опыт: `{vacancy.experience}`")
    st.markdown(f"Навыки: {vacancy.skills}")
    st.markdown(f"[Открыть вакансию]({vacancy.url})")
    st.markdown("**Описание:**")
    st.markdown(_build_description(vacancy, expanded))

    label = "Скрыть" if expanded else "Показать все"
    st.button(label, key=f"toggle_{vacancy.id}", on_click=_toggle_description, args=(vacancy.id,))
