"""
Streamlit chat UI for the same ConversationSession main.py runs on the CLI.
Run with: streamlit run chat_app.py
"""

import streamlit as st

from config import CLINIC_NAME
from session import ConversationSession

st.set_page_config(page_title=f"{CLINIC_NAME} Assistant", page_icon="💬")

if "session" not in st.session_state:
    st.session_state.session = ConversationSession()
if "history" not in st.session_state:
    st.session_state.history = [("assistant", st.session_state.session.opening_message())]

with st.sidebar:
    st.subheader(CLINIC_NAME)
    st.caption("Book, reschedule, or cancel an appointment, check availability, or clinic hours.")
    if st.button("Start over"):
        st.session_state.session.full_reset()
        st.session_state.history = [("assistant", st.session_state.session.opening_message())]
        st.rerun()
    with st.expander("Last structured output"):
        st.json(st.session_state.get("last_structured_output") or {})

st.title(f"{CLINIC_NAME} Assistant")

for role, text in st.session_state.history:
    with st.chat_message(role):
        st.write(text)

user_message = st.chat_input("Type a message...")
if user_message:
    st.session_state.history.append(("user", user_message))
    with st.chat_message("user"):
        st.write(user_message)

    result = st.session_state.session.handle_message(user_message)
    st.session_state.last_structured_output = result["structured_output"]

    st.session_state.history.append(("assistant", result["reply"]))
    with st.chat_message("assistant"):
        st.write(result["reply"])
