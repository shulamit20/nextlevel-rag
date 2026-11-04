"""Stage 0: checks that the API key, the network (NetFree) and both models work.

Run:  venv\\Scripts\\python check_connection.py
"""
import os
import sys

# Verify HTTPS certificates through Windows (needed behind NetFree; harmless elsewhere)
import truststore
truststore.inject_into_ssl()

from dotenv import load_dotenv
from llama_index.embeddings.google_genai import GoogleGenAIEmbedding
from llama_index.llms.google_genai import GoogleGenAI

import config

load_dotenv()
if not os.getenv("GOOGLE_API_KEY"):
    sys.exit("GOOGLE_API_KEY is missing. Copy .env.example to .env and paste your key.")

# 1. One embedding call: text -> vector
embed_model = GoogleGenAIEmbedding(model_name=config.EMBED_MODEL)
vector = embed_model.get_text_embedding("מחיר האולם הראשי במשמרת ערב")
print(f"[OK] Embedding ({config.EMBED_MODEL}): vector of {len(vector)} numbers")
print(f"     first 5: {[round(x, 4) for x in vector[:5]]}")

# 2. One LLM call: question -> text
llm = GoogleGenAI(model=config.LLM_MODEL)
response = llm.complete("Reply with exactly one word: OK")
print(f"[OK] LLM ({config.LLM_MODEL}): {response.text.strip()}")
