# Build instructions for Claude Code

> Paste this to Claude Code as the first message:
> **"Read CLAUDE.md, BUILD_PROMPT_EN.md and learning/prompt_draft.md, then start with build stage 0."**

---

## Ground rules
- Every design decision has already been made and is logged in **CLAUDE.md** (decision log). **They are binding.** Do not change any of them.
- Run into something that was not decided? (A function name is fine; a behavior, library or structure is not.) **Stop and ask.** Present 2–3 options + a recommendation, and wait for my answer.
- **No long explanations in the terminal** (Hebrew renders badly there). Write every explanation **in Hebrew** to `learning/NN_<stage>.md`; in the terminal only say which file to open.
- **Build in stages.** At the end of each stage: stop, explain (in a learning file), show me how to verify it, and wait for "continue".
- Environment: **Windows**, internet through **NetFree** (a filtering proxy that inspects HTTPS with its own certificate).

## Project structure (as decided)
- `data/` – 7 Markdown documents (in Hebrew; do not modify without approval)
- `ingest.py` – part A: builds the vector store
- `app.py` – part B: Streamlit UI and answering
- A config file – every value that may change (models, k, temperature, paths, office contact details, fixed texts)
- `.env` – the API key only. `.env` and `chroma_db/` go in `.gitignore`
- Any additional file (e.g. a module shared by ingest and app) – **propose it and wait for approval**

---

## Stage 0 – Environment and connectivity check
1. venv, `requirements.txt`, `.gitignore`, `.env.example`.
2. **Check the current documentation** for package names and model names (a Gemini Flash model on the free tier + a Gemini embedding model). Do not guess from memory.
3. A small test script: one embedding call + one LLM answer.
4. `CERTIFICATE_VERIFY_FAILED` means the NetFree certificate, not a bug – guide me on configuring Python to trust it. If the address is blocked – stop and tell me I need to ask NetFree to open `generativelanguage.googleapis.com`.

## Stage 1 – `ingest.py` (part A)
- Load `data/*.md`.
- Split **by Markdown structure (headings)**, with a safety cap of **512 tokens** (a longer section is also split by tokens). No overlap.
- Metadata per chunk: document name + the section's heading path (used to display sources).
- Embeddings with Gemini.
- ChromaDB **persisted to disk** (`chroma_db/`), with **cosine set explicitly** (the default is L2).
- On every run: **delete the store and rebuild from scratch.**
- At the end, print: number of chunks, and for each chunk its source + first 80 characters (so I can inspect the splitting).

## Stage 2 – Retrieval (no LLM yet)
- A function: question → the 3 nearest chunks (**k=3**) with score and source.
- Run it on several questions from `REVIEW_GUIDE.md` and show me what was retrieved – **before** connecting the LLM.

## Stage 3 – Answering
- The approved prompt: `learning/prompt_draft.md` (verbatim, in Hebrew; any wording change needs approval).
- **Temperature 0.2.**
- The LLM returns: `answer`, `status` (`answered` / `missing` / `out_of_scope`), `has_price`.
- **The code** (not the LLM) appends:
  - `status == "missing"` → the office contact line (from the config file)
  - `has_price == true` → "המחיר הסופי ייקבע בעת ההזמנה."
  - `out_of_scope` → nothing
- **Open question – ask me:** what happens if the LLM returns a format that cannot be parsed?

## Stage 4 – Follow-up questions
- History: the last **3 question–answer pairs**.
- **First question** – straight to retrieval. **Follow-up question** – an LLM call rewrites it into a standalone question, and only then embedding + retrieval.
- **Binding rule:** history is sent **only** to the rewrite step. The answer step receives **only** the (rewritten) question + the chunks. History is never a source of facts.
- Do **not** build a "structured conversation state" – only if testing shows a need, and only with my approval.

## Stage 5 – Streamlit UI
- **Right-to-left** layout.
- Chat with history (`st.session_state`).
- Under each answer: a collapsible **"▸ מקורות"** (sources) section, closed by default.
- Anything else on the screen (clear button, sidebar, etc.) – **propose and wait for approval.**

## Stage 6 – Testing
- A list of test questions + expected answers, based on "details especially suited for testing" in `REVIEW_GUIDE.md`:
  exact numbers, "traps", multi-document questions, questions outside the knowledge base, out-of-scope questions, very short questions, follow-ups,
  and **one long conversation** (an early detail such as "200 guests", then after 5 messages "how much will it cost?").
- I run them and mark pass/fail. Tuning (k, temperature, etc.) – only with my approval, and logged in CLAUDE.md.

## Stage 7 – Documentation
- README: how to run, architecture (the two parts), and the main decisions with their reasons (from the decision log).

---

## Never
- Put the API key in code or commit it to git.
- Change documents in `data/` or the prompt without approval.
- Add libraries, files or behaviors that were not decided without asking.
- commit / push without an explicit request.
