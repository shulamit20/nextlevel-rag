"""Part B: answers a customer question.

Flow: (follow-up only) rewrite into a standalone question -> retrieve chunks -> LLM answer
-> the code appends the fixed texts.
Binding rule: the history is sent ONLY to the rewrite step. The answer step gets only
the (rewritten) question and the chunks, so the history is never a source of facts.
"""
import logging
import os
import re
import time
from difflib import SequenceMatcher
from typing import Literal

import httpx
from google.genai import errors as genai_errors
from llama_index.core import PromptTemplate
from llama_index.llms.google_genai import GoogleGenAI
from pydantic import BaseModel

import config
import rag

# Created once, not on every call: creating GoogleGenAI asks Google for the model's
# details (~1 s). Requires the API key to be loaded (load_dotenv) before importing this file.
# max_retries=0 because retries are handled by call_with_retries below.
answer_llm = GoogleGenAI(
    model=config.LLM_MODEL, temperature=config.ANSWER_TEMPERATURE, max_retries=0
)
rewrite_llm = GoogleGenAI(
    model=config.LLM_MODEL, temperature=config.REWRITE_TEMPERATURE, max_retries=0
)

# Raw JSON log: shows exactly what the model returned (e.g. an answer cut at an unescaped ")
json_log = logging.getLogger("llm_json")
if not json_log.handlers:  # Streamlit may import this file again; add the handler once
    os.makedirs(os.path.dirname(config.LLM_JSON_LOG), exist_ok=True)
    handler = logging.FileHandler(config.LLM_JSON_LOG, encoding="utf-8")
    handler.setFormatter(logging.Formatter("%(asctime)s %(message)s"))
    json_log.addHandler(handler)
    json_log.setLevel(logging.INFO)
    json_log.propagate = False


class LLMReply(BaseModel):
    """The structure Gemini must return (enforced by the API, not only by the prompt)."""
    answer: str
    status: Literal["answered", "missing", "out_of_scope"]


class RewriteReply(BaseModel):
    """The structure the rewrite step must return. Field order matters: the model
    decides whether the question depends on the conversation before writing it."""
    depends_on_history: bool         # False -> the code ignores the rewrite entirely
    question: str                    # as asked, or rewritten as a standalone question
    details_from_history: list[str]  # details taken from the conversation; empty if none


# --- Errors and retries -------------------------------------------------------------

def is_temporary(error):
    """Network drop or server overload - worth trying again."""
    if isinstance(error, genai_errors.APIError):
        return error.code in (429, 500, 502, 503, 504)
    return isinstance(error, (httpx.TransportError, ConnectionError))


def call_with_retries(func, *args):
    """Retries temporary errors, waiting 1, 2, 4 seconds."""
    for attempt in range(config.NETWORK_RETRIES + 1):
        try:
            return func(*args)
        except Exception as error:
            if not is_temporary(error) or attempt == config.NETWORK_RETRIES:
                raise
            time.sleep(2 ** attempt)


def call_with_output_retry(func, *args):
    """Like call_with_retries, plus one more try if the LLM returned invalid output."""
    try:
        return call_with_retries(func, *args)
    except Exception as error:
        if is_temporary(error):
            raise
        return call_with_retries(func, *args)


# --- The two LLM steps --------------------------------------------------------------

def predict_json(llm, output_cls, prompt):
    """LLM call in the API's JSON mode (schema enforced by the API).
    Logs the raw JSON, then parses it strictly: invalid JSON raises and is retried."""
    raw = llm.complete(
        prompt,
        generation_config={"response_mime_type": "application/json", "response_schema": output_cls},
    ).text
    json_log.info("%s %s", output_cls.__name__, raw)
    return output_cls.model_validate_json(raw)


def rewrite_question(question, history):
    """Question + recent history -> RewriteReply (standalone question + details taken from history)."""
    history_text = "\n\n".join(f"לקוח: {q}\nנציג: {a}" for q, a in history)
    prompt = PromptTemplate(config.REWRITE_PROMPT).format(history=history_text, question=question)
    reply = predict_json(rewrite_llm, RewriteReply, prompt)
    if not reply.question.strip():
        raise ValueError("Empty rewrite")
    return reply


def answer_from_chunks(question, chunks):
    """Question + retrieved chunks -> LLMReply. Receives no history."""
    context = "\n\n---\n\n".join(c["llm_text"] for c in chunks)
    prompt = PromptTemplate(config.ANSWER_PROMPT).format(context=context, question=question)
    reply = predict_json(answer_llm, LLMReply, prompt)
    if not reply.answer.strip():
        raise ValueError("Empty answer")
    return reply


# --- The full flow ------------------------------------------------------------------

def ask(index, question, history):
    """history: all (question, answer) pairs so far; only the last HISTORY_PAIRS are used.

    Returns: answer (text to show), status, sources, search_question (after rewriting).
    """
    search_question = question
    details = []
    try:
        if history:
            rewrite = call_with_output_retry(
                rewrite_question, question, history[-config.HISTORY_PAIRS:]
            )
            if rewrite.depends_on_history:
                search_question = rewrite.question
                details = rewrite.details_from_history
            else:
                # Standalone: never take details from history. The spelling-corrected version
                # is used only if it stays close to the original
                ratio = SequenceMatcher(None, question, rewrite.question).ratio()
                if ratio >= config.TYPO_FIX_MIN_RATIO:
                    search_question = rewrite.question
                json_log.info("typo-fix ratio %.3f -> %s", ratio, search_question)
        chunks = call_with_retries(rag.retrieve, index, search_question)
        reply = call_with_output_retry(answer_from_chunks, search_question, chunks)
    except Exception:
        logging.exception("Answering failed")
        return {
            "answer": f"{config.ERROR_MESSAGE}\n\n{config.OFFICE_LINE}",
            "status": "error",
            "sources": [],
            "search_question": search_question,
        }

    # Fixed texts are added by the code, so they always appear and are worded the same
    # One way to write shekels in every answer
    text = re.sub(r'ש[״"]ח', "₪", reply.answer)
    if details:
        text = config.HISTORY_DETAILS_LINE.format(details=", ".join(details)) + "\n\n" + text
    if reply.status == "missing":
        text += f"\n\n{config.OFFICE_LINE}"

    return {
        "answer": text,
        "status": reply.status,
        "sources": chunks,
        "search_question": search_question,
        "details_from_history": details,
    }
