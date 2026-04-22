"""Streamlit chat UI for AI Job Finder frontend."""

from __future__ import annotations

import streamlit as st

from constants.messages import (
    ASSISTANT_RUNNING_MESSAGE,
    CHAT_INPUT_PLACEHOLDER,
    INITIAL_ASSISTANT_MESSAGE,
)
from constants.ui import (
    CHAT_ASSISTANT_NAME,
    CHAT_TITLE,
    PAGE_ICON,
    PAGE_LAYOUT,
    SESSION_MESSAGES_KEY,
    SESSION_VACANCY_EXPANDED_KEY,
)
from dto.chat_dto import ChatMessageDto
from services.chat_service import ChatService
from ui.vacancy_view import render_vacancy_card


def _init_state() -> None:
    """Initialize Streamlit session state for chat history."""
    if SESSION_MESSAGES_KEY not in st.session_state:
        st.session_state[SESSION_MESSAGES_KEY] = [
            ChatMessageDto(
                role="assistant",
                content=INITIAL_ASSISTANT_MESSAGE,
            )
        ]
    if SESSION_VACANCY_EXPANDED_KEY not in st.session_state:
        st.session_state[SESSION_VACANCY_EXPANDED_KEY] = {}


def _render_messages() -> None:
    """Render existing chat messages."""
    for index, message in enumerate(st.session_state[SESSION_MESSAGES_KEY]):
        with st.chat_message(message.role):
            st.markdown(message.content)
            vacancies = message.vacancies
            if vacancies is None and message.vacancy is not None:
                vacancies = [message.vacancy]
            if not vacancies:
                continue
            for vacancy_index, vacancy in enumerate(vacancies):
                render_vacancy_card(
                    vacancy,
                    message_index=index,
                    vacancy_index=vacancy_index,
                )


def _append_user_message(prompt: str) -> None:
    """Append one user message to history."""
    st.session_state[SESSION_MESSAGES_KEY].append(
        ChatMessageDto(role="user", content=prompt)
    )


def _append_assistant_response(prompt: str) -> None:
    """Generate and append assistant response with vacancy."""
    chat_service = ChatService()
    response = chat_service.build_response(prompt)
    st.session_state[SESSION_MESSAGES_KEY].append(response)


def main() -> None:
    """Run Streamlit application entrypoint."""
    st.set_page_config(page_title=CHAT_TITLE, page_icon=PAGE_ICON, layout=PAGE_LAYOUT)
    st.title(CHAT_TITLE)
    st.caption(f"Чат-ассистент: {CHAT_ASSISTANT_NAME}")

    _init_state()
    _render_messages()

    prompt = st.chat_input(CHAT_INPUT_PLACEHOLDER)
    if not prompt:
        return

    _append_user_message(prompt)
    with st.chat_message("assistant"):
        with st.spinner(ASSISTANT_RUNNING_MESSAGE):
            _append_assistant_response(prompt)
    st.rerun()


if __name__ == "__main__":
    main()
