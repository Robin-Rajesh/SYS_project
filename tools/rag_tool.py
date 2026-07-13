"""
rag_tool.py — Policy Document Search Tool (RAG with pgvector)
==============================================================
LangChain Tool that:
  1. Loads all .txt policy documents from docs/
  2. Chunks them with RecursiveCharacterTextSplitter
  3. Embeds with Google gemini-embedding-001 (MRL @ 1536-dim via API)
  4. Stores / loads from a pgvector store on Supabase (or local fallback)
  5. Retrieves top-4 relevant chunks for any policy question
"""

import os
import time
from langchain_core.tools import tool
from langchain_community.document_loaders import TextLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_postgres import PGVector
from langchain_google_genai import GoogleGenerativeAIEmbeddings

# Import project configuration
import config
from tools.sql_tool import get_engine

# ═══════════════════════════════════════════════════════════════
# 1. EMBEDDING MODEL (loaded once at module level)
# ═══════════════════════════════════════════════════════════════

_embeddings = GoogleGenerativeAIEmbeddings(
    model=config.EMBEDDING_MODEL,
    google_api_key=config.GOOGLE_API_KEY,
    output_dimensionality=config.EMBEDDING_DIMENSIONS,  # MRL truncation: 1536-dim
)

# ═══════════════════════════════════════════════════════════════
# 2. BUILD OR LOAD THE VECTOR STORE
# ═══════════════════════════════════════════════════════════════

class LocalVectorStore:
    def __init__(self, embeddings):
        self.embeddings = embeddings
        self.documents = []
        self.vectors = []
        
    def add_documents(self, documents):
        self.documents.extend(documents)
        texts = [doc.page_content for doc in documents]
        self.vectors.extend(self.embeddings.embed_documents(texts))
        
    def similarity_search(self, query: str, k: int = 4):
        if not self.documents:
            return []
        import numpy as np
        query_vec = np.array(self.embeddings.embed_query(query))
        doc_vecs = np.array(self.vectors)
        # Cosine similarity
        scores = np.dot(doc_vecs, query_vec) / (np.linalg.norm(doc_vecs, axis=1) * np.linalg.norm(query_vec) + 1e-9)
        top_k_idx = np.argsort(scores)[-k:][::-1]
        return [self.documents[i] for i in top_k_idx]

def _build_and_get_vector_store():
    """
    Connect to pgvector. If it's empty, load and chunk all .txt 
    documents from docs/, embed them, and persist to pgvector.
    In local mode, uses an in-memory vector store.
    """
    engine = get_engine()
    
    # Check if we should fallback to in-memory/sqlite vector store if not cloud
    if not config.IS_CLOUD:
        print("[RAG] Using local in-memory vector store for SQLite mode.")
        vector_store = LocalVectorStore(embeddings=_embeddings)
    else:
        vector_store = PGVector(
            embeddings=_embeddings,
            collection_name="policy_docs",
            connection=engine,
            use_jsonb=True,
        )

        try:
            # Check if collection is empty
            with engine.connect() as conn:
                from sqlalchemy import text
                res = conn.execute(text("SELECT COUNT(*) FROM langchain_pg_embedding WHERE collection_id = (SELECT uuid FROM langchain_pg_collection WHERE name = 'policy_docs' LIMIT 1)")).scalar()
                
            if res and res > 0:
                print(f"[RAG] Vector store already populated with {res} chunks.")
                return vector_store
        except Exception as e:
            print(f"[RAG] Tables might not exist yet, proceeding to populate. ({e})")

    docs_dir = str(config.DOCS_DIR)
    all_documents = []

    for filename in os.listdir(docs_dir):
        if filename.endswith(".txt"):
            filepath = os.path.join(docs_dir, filename)
            loader = TextLoader(filepath, encoding="utf-8")
            documents = loader.load()
            for doc in documents:
                doc.metadata["source"] = filename
            all_documents.extend(documents)

    if not all_documents:
        print(f"[RAG] No .txt files found in {docs_dir}.")
        return vector_store

    splitter = RecursiveCharacterTextSplitter(
        chunk_size=500,
        chunk_overlap=50,
    )
    chunks = splitter.split_documents(all_documents)
    print(f"[RAG] Split {len(all_documents)} documents into {len(chunks)} chunks.")

    # Embed and persist
    vector_store.add_documents(chunks)
    print(f"[RAG] Vector store built and populated.")
    return vector_store

# We delay initialization until the first query to avoid DB connection issues on import
_vector_store = None

# ═══════════════════════════════════════════════════════════════
# 3. RETRIEVAL FUNCTION
# ═══════════════════════════════════════════════════════════════

def _retrieve(query: str, k: int = 4) -> str:
    global _vector_store
    if _vector_store is None:
        _vector_store = _build_and_get_vector_store()

    try:
        t_rag = time.perf_counter()
        results = _vector_store.similarity_search(query, k=k)
        print(f"⏱️ [PERF] rag_tool.similarity_search: {time.perf_counter()-t_rag:.3f}s ({len(results)} chunks)")
    except Exception as e:
        print(f"[RAG] Retrieval failed: {e}")
        return "DATA UNAVAILABLE: Policy retrieval failed (ensure pgvector is configured)."

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
