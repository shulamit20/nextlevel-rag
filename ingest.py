"""Part A: builds the vector store from the documents in data/.

Run again whenever a document changes - the store is deleted and rebuilt from scratch.
Run:  .\\venv\\Scripts\\python .\\ingest.py
"""
import os

# Verify HTTPS certificates through Windows (needed behind NetFree; harmless elsewhere)
import truststore
truststore.inject_into_ssl()

from dotenv import load_dotenv
from llama_index.core import SimpleDirectoryReader, StorageContext, VectorStoreIndex
from llama_index.core.node_parser import MarkdownNodeParser, SentenceSplitter
from llama_index.vector_stores.chroma import ChromaVectorStore

import config
import rag

load_dotenv()

# 1. Load: one Document per file. Metadata = file name only (no disk path,
#    so the path does not end up inside the embedding)
documents = SimpleDirectoryReader(
    config.DATA_DIR,
    required_exts=[".md"],
    file_metadata=lambda path: {"file_name": os.path.basename(path)},
).load_data()
print(f"Loaded {len(documents)} documents")

# 2. Split: by Markdown headings (adds 'header_path' metadata),
#    then a safety cap - a section longer than the cap is split again by tokens
nodes = MarkdownNodeParser().get_nodes_from_documents(documents)
nodes = SentenceSplitter(
    chunk_size=config.CHUNK_MAX_TOKENS,
    chunk_overlap=config.CHUNK_OVERLAP,
).get_nodes_from_documents(nodes)

# Drop heading-only chunks (a heading followed directly by a sub-heading) - they hold no information
def is_heading_only(node):
    text = node.get_content().strip()
    return text.startswith("#") and "\n" not in text

nodes = [n for n in nodes if not is_heading_only(n)]

# 3 + 4. Embed every chunk and store it in a fresh ChromaDB collection on disk
collection = rag.create_empty_collection()
storage_context = StorageContext.from_defaults(
    vector_store=ChromaVectorStore(chroma_collection=collection)
)
VectorStoreIndex(nodes, storage_context=storage_context, embed_model=rag.get_embed_model())

# Report, to inspect the splitting
print(f"Stored {collection.count()} chunks in {config.CHROMA_DIR}/ "
      f"(collection '{config.COLLECTION_NAME}', distance: {collection.configuration['hnsw']['space']})\n")
for i, node in enumerate(nodes, 1):
    preview = " ".join(node.get_content().split())[:80]
    print(f"{i:2}. [{rag.chunk_source(node)}]")
    print(f"    {preview}")
