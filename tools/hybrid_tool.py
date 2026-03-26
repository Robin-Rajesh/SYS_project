"""
hybrid_tool.py — Hybrid Search: SQL Records + RAG Context Side-by-Side
========================================================================
Fires both retrieval paths concurrently using Python threads:
  1. SQL path  → exact, structured records from SQLite
  2. RAG path  → semantic document chunks from ChromaDB

Returns a structured dict consumed by the /api/hybrid-search endpoint
so the frontend can render both lanes in parallel panels.
"""

import json
import re
import concurrent.futures
from typing import Dict, Any, List, Optional

import pandas as pd
from sqlalchemy import text
from langchain_google_genai import ChatGoogleGenerativeAI

import config
from tools.sql_tool import get_engine, get_schema, _is_read_only
from tools.rag_tool import _retrieve


# ═══════════════════════════════════════════════════════════════
# 1. SQL LANE — Ask the LLM to auto-generate SQL from a NL query
# ═══════════════════════════════════════════════════════════════

def _nl_to_sql(natural_query: str) -> str:
    """
    Convert a natural language question to a SELECT statement using Gemini.
    Returns the raw SQL string.
    """
    llm = ChatGoogleGenerativeAI(
        model=config.MODEL_NAME,
        google_api_key=config.GOOGLE_API_KEY,
        temperature=0,
    )
    schema = get_schema()
    prompt = f"""You are a SQL expert. Convert the user question below into a single valid SQLite SELECT query.
Return ONLY the SQL — no markdown, no explanation, no semicolons.

DATABASE SCHEMA:
{schema}

USER QUESTION:
{natural_query}

SQL:"""
    response = llm.invoke(prompt)
    sql = response.content.strip()
    # Strip markdown fences if present
    sql = re.sub(r"```sql", "", sql, flags=re.IGNORECASE)
    sql = sql.replace("```", "").strip().rstrip(";")
    return sql


def _run_sql_lane(query: str) -> Dict[str, Any]:
    """
    Execute the SQL lane:
      - Convert NL → SQL
      - ATTACH all sibling databases
      - Execute and return raw rows + generated SQL
    """
    import os
    from tools.sql_tool import _current_db_uri

    try:
        sql = _nl_to_sql(query)

        if not _is_read_only(sql):
            return {
                "success": False,
                "sql": sql,
                "rows": [],
                "columns": [],
                "error": "Generated SQL contains write operations — blocked for safety.",
            }

        engine = get_engine()
        db_files = [f for f in os.listdir(config.DATA_DIR) if f.endswith((".db", ".sqlite"))]
        active_db_name = os.path.basename(_current_db_uri.split("///")[-1])

        with engine.connect() as conn:
            for db_file in db_files:
                if db_file != active_db_name:
                    alias = re.sub(r"[^a-zA-Z0-9_]", "_", os.path.splitext(db_file)[0])
                    attach_path = str(config.DATA_DIR / db_file).replace("\\", "/")
                    try:
                        conn.execute(text(f"ATTACH DATABASE '{attach_path}' AS {alias}"))
                    except Exception:
                        pass
            df = pd.read_sql(text(sql), conn)

        if df.empty:
            return {"success": True, "sql": sql, "rows": [], "columns": list(df.columns), "error": None}

        return {
            "success": True,
            "sql": sql,
            "columns": list(df.columns),
            "rows": df.head(100).to_dict(orient="records"),
            "total_rows": len(df),
            "error": None,
        }

    except Exception as e:
        return {
            "success": False,
            "sql": "",
            "rows": [],
            "columns": [],
            "error": str(e),
        }


# ═══════════════════════════════════════════════════════════════
# 2. RAG LANE — Semantic search over document chunks
# ═══════════════════════════════════════════════════════════════

def _run_rag_lane(query: str, k: int = 5) -> Dict[str, Any]:
    """
    Execute the RAG lane:
      - Similarity search against ChromaDB
      - Parse each chunk into a structured object with source + text
    """
    try:
        raw = _retrieve(query, k=k)
        if "DATA UNAVAILABLE" in raw:
            return {"success": True, "chunks": [], "error": None}

        chunks: List[Dict] = []
        for block in raw.split("---"):
            block = block.strip()
            if not block:
                continue
            source_match = re.match(r"\[Source: (.+?)\]", block)
            source = source_match.group(1) if source_match else "Unknown"
            content = re.sub(r"\[Source: .+?\]\n?", "", block).strip()
            if content:
                chunks.append({"source": source, "content": content})

        return {"success": True, "chunks": chunks, "error": None}

    except Exception as e:
        return {"success": False, "chunks": [], "error": str(e)}


# ═══════════════════════════════════════════════════════════════
# 3. AI SYNTHESIS — merge both results into a brief insight
# ═══════════════════════════════════════════════════════════════

def _synthesize(query: str, sql_result: Dict, rag_result: Dict) -> str:
    """
    Use the LLM to write a 2-3 sentence synthesis combining the
    SQL data facts with the document context.
    Returns a plain-text insight string.
    """
    llm = ChatGoogleGenerativeAI(
        model=config.MODEL_NAME,
        google_api_key=config.GOOGLE_API_KEY,
        temperature=0,
    )

    sql_summary = "No SQL results."
    if sql_result.get("success") and sql_result.get("rows"):
        sample_rows = sql_result["rows"][:5]
        sql_summary = f"Top {len(sample_rows)} rows: {json.dumps(sample_rows)}"

    rag_summary = "No document context."
    if rag_result.get("chunks"):
        rag_summary = "\n".join(c["content"] for c in rag_result["chunks"][:2])

    prompt = f"""You are a concise data analyst assistant. Write 2-3 insightful sentences answering the question below.
Combine the structured database data and the document context. Be specific, cite numbers where available.

QUESTION: {query}

DATABASE DATA:
{sql_summary}

DOCUMENT CONTEXT:
{rag_summary}

INSIGHT:"""

    try:
        response = llm.invoke(prompt)
        return response.content.strip()
    except Exception:
        return "Could not generate synthesis — please review the data and document panels manually."


# ═══════════════════════════════════════════════════════════════
# 4. PUBLIC ENTRY POINT
# ═══════════════════════════════════════════════════════════════

def run_hybrid_search(query: str) -> Dict[str, Any]:
    """
    Fire both SQL and RAG lanes concurrently using a thread pool,
    then synthesize the combined results.

    Returns:
    {
      "query": str,
      "sql": { "success", "sql", "columns", "rows", "total_rows", "error" },
      "rag": { "success", "chunks", "error" },
      "synthesis": str
    }
    """
    with concurrent.futures.ThreadPoolExecutor(max_workers=2) as pool:
        sql_future = pool.submit(_run_sql_lane, query)
        rag_future = pool.submit(_run_rag_lane, query)
        sql_result = sql_future.result()
        rag_result = rag_future.result()

    synthesis = _synthesize(query, sql_result, rag_result)

    return {
        "query": query,
        "sql": sql_result,
        "rag": rag_result,
        "synthesis": synthesis,
    }
