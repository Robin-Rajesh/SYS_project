"""
rag_tool.py — Policy Document Search Tool (RAG with ChromaDB)
==============================================================
LangChain Tool that:
  1. Loads all .txt policy documents from docs/
  2. Chunks them with RecursiveCharacterTextSplitter
  3. Embeds with HuggingFace sentence-transformers (local, free)
  4. Stores / loads from a persistent ChromaDB vector store
  5. Retrieves top-4 relevant chunks for any policy question
"""

import os
from langchain_core.tools import tool
from langchain_community.document_loaders import TextLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_community.vectorstores import Chroma
from langchain_community.embeddings import HuggingFaceEmbeddings

# Import project configuration
import config

# ═══════════════════════════════════════════════════════════════
# 1. EMBEDDING MODEL (loaded once at module level)
# ═══════════════════════════════════════════════════════════════
# Using sentence-transformers "all-MiniLM-L6-v2" — small, fast,
# runs 100 % locally with zero API cost.  The first import will
# download the model weights (~80 MB) if they are not cached.

_embeddings = HuggingFaceEmbeddings(
    model_name=config.EMBEDDING_MODEL,
    model_kwargs={"device": "cpu"},          # Force CPU (safe on all machines)
    encode_kwargs={"normalize_embeddings": True},
)

# ═══════════════════════════════════════════════════════════════
# 2. BUILD OR LOAD THE VECTOR STORE
# ═══════════════════════════════════════════════════════════════

def _vector_store_exists() -> bool:
    """
    Check whether the ChromaDB persistence directory is non-empty.
    If it contains files, we assume the store was already built on
    a previous run and simply load it.
    """
    vs_dir = str(config.VECTOR_STORE_DIR)
    return os.path.isdir(vs_dir) and len(os.listdir(vs_dir)) > 0


def _build_vector_store() -> Chroma:
    """
    Load all .txt documents from docs/, chunk them, embed them,
    and persist the ChromaDB collection to disk.
    """
    docs_dir = str(config.DOCS_DIR)
    all_documents = []

    # Load every .txt file inside the docs/ directory
    for filename in os.listdir(docs_dir):
        if filename.endswith(".txt"):
            filepath = os.path.join(docs_dir, filename)
            loader = TextLoader(filepath, encoding="utf-8")
            documents = loader.load()
            # Attach the source filename as metadata so we can cite it
            for doc in documents:
                doc.metadata["source"] = filename
            all_documents.extend(documents)

    if not all_documents:
        raise FileNotFoundError(
            f"No .txt files found in {docs_dir}. "
            "Run generate_data.py first to create the policy documents."
        )

    # Split documents into smaller chunks for more precise retrieval
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=500,       # ~500 characters per chunk
        chunk_overlap=50,     # 50 character overlap to preserve context at boundaries
    )
    chunks = splitter.split_documents(all_documents)
    print(f"[RAG] Split {len(all_documents)} documents into {len(chunks)} chunks.")

    # Embed and persist to ChromaDB
    vector_store = Chroma.from_documents(
        documents=chunks,
        embedding=_embeddings,
        persist_directory=str(config.VECTOR_STORE_DIR),
    )
    print(f"[RAG] Vector store built and persisted to {config.VECTOR_STORE_DIR}")
    return vector_store


def _load_vector_store() -> Chroma:
    """Load an existing persisted ChromaDB collection from disk."""
    return Chroma(
        persist_directory=str(config.VECTOR_STORE_DIR),
        embedding_function=_embeddings,
    )


def _get_vector_store() -> Chroma:
    """Return the vector store — build it on first run, load thereafter."""
    if _vector_store_exists():
        print("[RAG] Loading existing vector store from disk …")
        return _load_vector_store()
    else:
        print("[RAG] Building vector store for the first time …")
        return _build_vector_store()


# Initialize once at module load time
_vector_store = _get_vector_store()

# ═══════════════════════════════════════════════════════════════
# 3. RETRIEVAL FUNCTION
# ═══════════════════════════════════════════════════════════════

def _retrieve(query: str, k: int = 4) -> str:
    """
    Retrieve the top-k most relevant document chunks for the query.
    Format each result with its source filename for transparency.
    """
    results = _vector_store.similarity_search(query, k=k)

    if not results:
        return "DATA UNAVAILABLE: No relevant policy information found."

    formatted_chunks = []
    for doc in results:
        source = doc.metadata.get("source", "unknown")
        formatted_chunks.append(
            f"[Source: {source}]\n{doc.page_content}\n---"
        )

    return "\n\n".join(formatted_chunks)

# ═══════════════════════════════════════════════════════════════
# 4. LANGCHAIN TOOL DEFINITION
# ═══════════════════════════════════════════════════════════════

@tool
def policy_search_tool(query: str) -> str:
    """Use this to search internal sales policy documents, discount
    approval rules, and product catalog. Use for any question about
    policies, discount limits, approval requirements, or products."""
    return _retrieve(query)
