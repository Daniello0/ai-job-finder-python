"""Streamlit chat UI for AI Job Finder frontend."""

from __future__ import annotations

import streamlit as st

from constants.ui import CHAT_ASSISTANT_NAME, CHAT_TITLE
from dto.chat_dto import ChatMessageDto
from services.chat_service import ChatService
from ui.vacancy_view import render_vacancy_card


def _init_state() -> None:
    """Initialize Streamlit session state for chat history."""
    if "messages" not in st.session_state:
        st.session_state.messages = [
            ChatMessageDto(
                role="assistant",
                content=(
                    "Опишите ваш опыт, стек и ожидания — я подберу вакансию "
                    "и покажу ключевые детали."
                ),
            )
        ]
    if "vacancy_expanded" not in st.session_state:
        st.session_state.vacancy_expanded = {}


def _render_messages() -> None:
    """Render existing chat messages."""
    for message in st.session_state.messages:
        with st.chat_message(message.role):
            st.markdown(message.content)
            if message.vacancy is not None:
                render_vacancy_card(message.vacancy)


def _append_user_message(prompt: str) -> None:
    """Append one user message to history."""
    st.session_state.messages.append(ChatMessageDto(role="user", content=prompt))


def _append_assistant_response(prompt: str) -> None:
    """Generate and append assistant response with vacancy."""
    chat_service = ChatService()
    response = chat_service.build_response(prompt)
    st.session_state.messages.append(response)


def main() -> None:
    """Run Streamlit application entrypoint."""
    st.set_page_config(page_title=CHAT_TITLE, page_icon="💼", layout="centered")
    st.title(CHAT_TITLE)
    st.caption(f"Чат-ассистент: {CHAT_ASSISTANT_NAME}")

    _init_state()
    _render_messages()

    prompt = st.chat_input("Например: Junior Python, FastAPI, удаленно в Минске")
    if not prompt:
        return

    _append_user_message(prompt)
    _append_assistant_response(prompt)
    st.rerun()


if __name__ == "__main__":
    main()
