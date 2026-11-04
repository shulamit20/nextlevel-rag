"""Shows the bot's answers to test questions, without the UI.

Run (after ingest.py):  .\\venv\\Scripts\\python .\\check_answers.py
"""
# Verify HTTPS certificates through Windows (needed behind NetFree; harmless elsewhere)
import truststore
truststore.inject_into_ssl()

import time

from dotenv import load_dotenv

load_dotenv()

import answer
import rag

# Each conversation is a list of questions asked one after the other (history carries over)
CONVERSATIONS = [
    ["כמה עולה האולם הראשי במשמרת ערב?"],                          # price + noise trap
    ["כמה יעלה ערב באולם הבדולח ל-200 אורחים עם תפריט בשרי?"],     # price calculation, two documents
    ["כמה עולה DJ?"],                                               # missing info
    ["מה מזג האוויר מחר בירושלים?"],                                # out of scope
    ["כמה עולה אולם הגן בבוקר?", "ובערב?", "יש שם חניה?"],          # follow-up questions
]

# Free tier allows 15 requests/minute and a follow-up question uses 2 -> pause between questions
PAUSE_SECONDS = 9

index = rag.load_index()

for questions in CONVERSATIONS:
    history = []
    print("\n" + "=" * 70)
    for question in questions:
        time.sleep(PAUSE_SECONDS)
        result = answer.ask(index, question, history)
        print(f"\nQ: {question}")
        if result["search_question"] != question:
            print(f"   rewritten: {result['search_question']}")
        print(f"   status: {result['status']}   from history: {result.get('details_from_history')}")
        print("   sources: " + " | ".join(c["source"] for c in result["sources"]))
        print(f"A: {result['answer']}")
        history.append((question, result["answer"]))
