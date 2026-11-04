"""Shared by ingest.py and app.py: the embedding model, the vector store and retrieval.

Keeping this in one place guarantees that building the store and searching it
use the same embedding model, the same collection and the same distance metric.
"""
import math

import chromadb
from llama_index.core import VectorStoreIndex
from llama_index.core.schema import MetadataMode
from llama_index.embeddings.google_genai import GoogleGenAIEmbedding
from llama_index.vector_stores.chroma import ChromaVectorStore

import config


def get_embed_model():
    # LlamaIndex sends task_type RETRIEVAL_DOCUMENT for chunks and RETRIEVAL_QUERY for questions
    return GoogleGenAIEmbedding(model_name=config.EMBED_MODEL)


def create_empty_collection():
    """Deletes the collection (if it exists) and creates a new, empty one with cosine distance."""
    client = chromadb.PersistentClient(path=config.CHROMA_DIR)
    if config.COLLECTION_NAME in [c.name for c in client.list_collections()]:
        client.delete_collection(config.COLLECTION_NAME)
    # ChromaDB's default is L2, so cosine must be set explicitly
    return client.create_collection(
        config.COLLECTION_NAME,
        configuration={"hnsw": {"space": "cosine"}},
    )


def load_index():
    """Opens the existing store (built by ingest.py) for searching."""
    client = chromadb.PersistentClient(path=config.CHROMA_DIR)
    collection = client.get_collection(config.COLLECTION_NAME)
    return VectorStoreIndex.from_vector_store(
        ChromaVectorStore(chroma_collection=collection),
        embed_model=get_embed_model(),
    )


def chunk_source(node):
    """'file name › heading › sub-heading' - used to display sources."""
    parts = [node.metadata["file_name"]]
    parts += [h for h in node.metadata.get("header_path", "").split("/") if h]
    first_line = node.get_content().split("\n", 1)[0]
    if first_line.startswith("#"):
        parts.append(first_line.lstrip("#").strip())
    return " › ".join(parts)


def retrieve(index, question, k=config.TOP_K):
    """Question -> the k nearest chunks, each with its text, source and similarity score."""
    results = index.as_retriever(similarity_top_k=k).retrieve(question)
    return [
        {
            "text": r.node.get_content(),
            # What the LLM sees: heading path + text (same as what was embedded)
            "llm_text": r.node.get_content(metadata_mode=MetadataMode.LLM),
            "source": chunk_source(r.node),
            # The Chroma integration reports exp(-distance); convert back to cosine
            # similarity (1 = same meaning, 0 = unrelated)
            "score": 1 + math.log(r.score),
        }
        for r in results
    ]
