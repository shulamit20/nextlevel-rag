"""Part B: the chat UI (Streamlit).

Run:  .\\venv\\Scripts\\streamlit run .\\app.py
"""
# Verify HTTPS certificates through Windows (needed behind NetFree; harmless elsewhere)
import truststore
truststore.inject_into_ssl()

import re

import streamlit as st
from dotenv import load_dotenv

load_dotenv()

import answer
import config
import rag

st.set_page_config(page_title="NextLevel Events")

# Right-to-left layout for Hebrew
st.markdown(
    """
    <style>
    .stApp, [data-testid="stChatMessageContent"], [data-testid="stChatInput"] textarea {
        direction: rtl;
        text-align: right;
    }
    /* Lists: bullets on the right. !important because Streamlit's own list styles
       (left padding, LTR) are injected after ours */
    [data-testid="stMarkdownContainer"] ul,
    [data-testid="stMarkdownContainer"] ol,
    [data-testid="stMarkdownContainer"] li {
        direction: rtl !important;
        text-align: right !important;
    }
    [data-testid="stMarkdownContainer"] ul,
    [data-testid="stMarkdownContainer"] ol {
        padding-left: 0 !important;
        padding-right: 1.5rem !important;
    }
    </style>
    """,
    unsafe_allow_html=True,
)


# In right-to-left text a number range ("09:00–17:00") is shown reversed ("17:00–09:00").
# Wrapping it in a left-to-right isolate (U+2066 ... U+2069) keeps its order.
# Chains like the phone 03-500-3000 are matched whole, so they stay in one piece.
NUMBER = r"\d(?:[\d:.,]*\d)?"  # ends with a digit, so a trailing comma stays outside
NUMBER_RANGE = re.compile(rf"{NUMBER}(?:\s*[–-]\s*{NUMBER})+")

# Markdown joins a line to the one before it (e.g. "סה״כ" glued to the last list item).
# Two spaces before a single newline make it a real line break, so every line stays separate.
SINGLE_NEWLINE = re.compile(r"(?<!\n)\n(?!\n)")


def show_text(text):
    """Display only: the stored text (sent to the rewrite step) stays unchanged."""
    text = NUMBER_RANGE.sub(lambda m: f"⁦{m.group(0)}⁩", text)
    st.markdown(SINGLE_NEWLINE.sub("  \n", text))


@st.cache_resource(show_spinner="טוען את מאגר הידע...")
def get_index():
    """Opened once per server, not on every question."""
    return rag.load_index()


def show_sources(sources):
    """Collapsible sources section, closed by default."""
    if not sources:
        return
    with st.expander("מקורות", expanded=False):
        for chunk in sources:
            st.markdown(f"**{chunk['source']}** · ציון {chunk['score']:.3f}")
            st.text(chunk["text"])


# Streamlit re-runs this whole file on every interaction; session_state survives re-runs
if "messages" not in st.session_state:
    st.session_state.messages = []  # everything shown in the chat
    st.session_state.history = []   # (question, answer) pairs, for follow-up questions

st.caption(config.PRICE_NOTE)  # once at the top, instead of under every answer with a price

for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        show_text(message["content"])
        show_sources(message.get("sources"))

question = st.chat_input("שאלו על אולמות, קייטרינג, שירותים, הזמנות ותשלומים")
if question:
    with st.chat_message("user"):
        show_text(question)

    with st.chat_message("assistant"):
        with st.spinner("..."):
            result = answer.ask(get_index(), question, st.session_state.history)
        show_text(result["answer"])
        show_sources(result["sources"])

    st.session_state.messages.append({"role": "user", "content": question})
    st.session_state.messages.append(
        {"role": "assistant", "content": result["answer"], "sources": result["sources"]}
    )
    st.session_state.history.append((question, result["answer"]))
