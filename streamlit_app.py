"""Streamlit UI for Food Verse AI.  Run:  streamlit run streamlit_app.py"""

import json

import streamlit as st

from foodverse import FoodVerseAgent
from foodverse.config import get_api_key

st.set_page_config(page_title="Food Verse AI", page_icon="🍽️", layout="centered")
st.title("🍽️ Food Verse AI")
st.caption("Multimodal food intelligence: snap a meal or describe it, get nutrition and diet insights.")

if get_api_key() is None:
    st.error("GROQ_API_KEY is not set. Copy `.env.example` to `.env` and add your Groq key, then restart.")
    st.stop()

if "agent" not in st.session_state:
    st.session_state.agent = FoodVerseAgent()
    st.session_state.chat = []  # list of (role, text, tool_calls)

with st.sidebar:
    st.header("Options")
    if st.button("New conversation"):
        st.session_state.agent.reset()
        st.session_state.chat = []
        st.rerun()
    show_tools = st.checkbox("Show tool calls", value=False)
    st.markdown("---")
    st.caption("Portion sizes from photos are estimates. Not medical advice.")

for role, text, tools in st.session_state.chat:
    with st.chat_message(role):
        st.markdown(text)
        if show_tools and tools:
            with st.expander("Tool calls"):
                for t in tools:
                    st.code(f"{t['tool']}({json.dumps(t['input'])})\n→ {t['output']}", language="text")

upload = st.file_uploader("Meal photo (optional)", type=["jpg", "jpeg", "png", "webp"])
if upload:
    st.image(upload, width=300)

prompt = st.chat_input("Describe your meal, ask a question, or just send the photo…")
new_photo = upload is not None and st.session_state.get("_sent_upload") != upload.file_id
if prompt or new_photo:
    prompt = prompt or ""
    image_bytes = upload.getvalue() if upload else None
    if upload:
        st.session_state._sent_upload = upload.file_id
    st.session_state.chat.append(("user", prompt or "📷 (photo)", []))
    with st.chat_message("user"):
        st.markdown(prompt or "📷 (photo)")
    with st.chat_message("assistant"):
        with st.spinner("Analyzing…"):
            try:
                result = st.session_state.agent.ask(prompt, image_bytes)
            except Exception as e:  # noqa: BLE001
                st.error(f"Something went wrong: {e}")
                st.stop()
        st.markdown(result.text)
    st.session_state.chat.append(("assistant", result.text, result.tool_calls))
