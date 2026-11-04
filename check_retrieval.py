"""Shows which chunks are retrieved for test questions - before any LLM is involved.

Run (after ingest.py):  .\\venv\\Scripts\\python .\\check_retrieval.py
"""
# Verify HTTPS certificates through Windows (needed behind NetFree; harmless elsewhere)
import truststore
truststore.inject_into_ssl()

from dotenv import load_dotenv

import config
import rag

# Based on "details especially suited for testing" in REVIEW_GUIDE.md
QUESTIONS = [
    "כמה עולה האולם הראשי במשמרת ערב?",                          # exact number
    "האם התפריט הטבעוני כולל שתייה?",                             # trap: it does not
    "יש חניון בגני הפנינה?",                                       # trap: no private parking
    "כמה יעלה ערב באולם הבדולח ל-200 אורחים עם תפריט בשרי?",     # combines two documents
    "כמה עולה DJ?",                                               # not in the documents
]

load_dotenv()
index = rag.load_index()

for question in QUESTIONS:
    print(f"\n=== {question}")
    for i, chunk in enumerate(rag.retrieve(index, question), 1):
        preview = " ".join(chunk["text"].split())[:100]
        print(f"  {i}. score {chunk['score']:.3f}  [{chunk['source']}]")
        print(f"     {preview}")
print(f"\n(k={config.TOP_K})")
