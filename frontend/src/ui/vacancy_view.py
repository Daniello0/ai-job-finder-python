"""UI components for vacancy rendering."""

from __future__ import annotations

import streamlit as st

from constants.ui import DESCRIPTION_PREVIEW_LENGTH, SESSION_VACANCY_EXPANDED_KEY
from dto.vacancy_dto import VacancyDto


def _build_description(vacancy: VacancyDto, expanded: bool) -> str:
    """Return full or shortened description based on toggle state."""
    if expanded or len(vacancy.description) <= DESCRIPTION_PREVIEW_LENGTH:
        return vacancy.description
    preview = vacancy.description[:DESCRIPTION_PREVIEW_LENGTH].rstrip()
    return f"{preview}..."


def _toggle_description(state_key: str) -> None:
    """Flip expanded state for one vacancy."""
    expanded_map = st.session_state[SESSION_VACANCY_EXPANDED_KEY]
    current = expanded_map.get(state_key, False)
    expanded_map[state_key] = not current


def render_vacancy_card(
    vacancy: VacancyDto, *, message_index: int, vacancy_index: int
) -> None:
    """Render vacancy details with description show more/hide."""
    state_key = f"vacancy_description_{message_index}_{vacancy_index}_{vacancy.id}"
    expanded = st.session_state[SESSION_VACANCY_EXPANDED_KEY].get(state_key, False)

    st.markdown(f"### Вакансия {vacancy_index + 1}")
    st.markdown(f"**{vacancy.title}**")
    st.markdown(f"Компания: **{vacancy.company}**")
    st.markdown(f"Зарплата: `{vacancy.salary}`")
    st.markdown(f"Частота выплат: `{vacancy.payment_frequency}`")
    st.markdown(f"Занятость: `{vacancy.employment}`")
    st.markdown(f"Формат найма: `{vacancy.hiring_format}`")
    st.markdown(f"График: `{vacancy.schedule}`")
    st.markdown(f"Часы работы: `{vacancy.hours}`")
    st.markdown(f"Формат работы: `{vacancy.work_format}`")
    st.markdown(f"Опыт: `{vacancy.experience}`")
    st.markdown(f"Навыки: {vacancy.skills}")
    if vacancy.cosine_distance is not None:
        st.markdown(f"Релевантность (cosine distance): `{vacancy.cosine_distance:.4f}`")
    st.markdown(f"[Открыть вакансию]({vacancy.url})")
    st.markdown("**Описание:**")
    st.markdown(_build_description(vacancy, expanded))

    label = "Скрыть" if expanded else "Показать все"
    st.button(
        label,
        key=f"toggle_{message_index}_{vacancy_index}_{vacancy.id}",
        on_click=_toggle_description,
        args=(state_key,),
    )
