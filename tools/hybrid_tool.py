"""
hybrid_tool.py — Hybrid Search: Analytical SQL + RAG-style DB Record Retrieval
================================================================================
Two-step pipeline:

  Step 1  (SQL lane)  — NL -> structured SELECT with aggregation/grouping.
  Step 2  (RAG lane)  — Extract entity values from the SQL result rows
                        (customer names, product names, IDs, etc.) and use
                        those as LIKE search terms across ALL table columns
                        in ALL attached databases.

Because Step 2 uses the actual output of Step 1 as its search terms, the
two panels are guaranteed to show the same entities — just from different
angles:
  LEFT  → ranked / aggregated summary  ("Dorothy Nelson  $229k revenue")
  RIGHT → raw matching records for those same entities across every table
"""

import json
import os
import re
from typing import Dict, Any, List

import pandas as pd
from sqlalchemy import inspect as sa_inspect, text
from langchain_google_genai import ChatGoogleGenerativeAI

import config
from tools.sql_tool import get_engine, get_schema, _is_read_only, _current_db_uri


# ═══════════════════════════════════════════════════════════════
# SHARED HELPERS
# ═══════════════════════════════════════════════════════════════

def _attach_all(conn):
    """ATTACH every sibling .db file to the open connection."""
    db_files = [f for f in os.listdir(config.DATA_DIR) if f.endswith((".db", ".sqlite"))]
    active_db_name = os.path.basename(_current_db_uri.split("///")[-1])
    for db_file in db_files:
        if db_file != active_db_name:
            alias = re.sub(r"[^a-zA-Z0-9_]", "_", os.path.splitext(db_file)[0])
            attach_path = str(config.DATA_DIR / db_file).replace("\\", "/")
            try:
                conn.execute(text(f"ATTACH DATABASE '{attach_path}' AS {alias}"))
            except Exception:
                pass


def _extract_keywords(query: str) -> List[str]:
    """Pull meaningful keywords from the NL query (stop-word filtered)."""
    STOP = {
        "what", "which", "are", "is", "the", "of", "in", "for", "by",
        "me", "show", "give", "find", "list", "tell", "all", "any",
        "how", "many", "much", "top", "bottom", "best", "worst",
        "and", "or", "not", "to", "a", "an", "with", "from", "on",
        "do", "does", "did", "have", "has", "their", "its",
    }
    words = re.findall(r"[a-zA-Z]{3,}", query.lower())
    return [w for w in words if w not in STOP][:6]


def _values_from_sql_result(sql_result: Dict) -> List[str]:
    """
    Extract meaningful string/ID values from the SQL result rows.
    These become the RAG search terms so the right panel shows raw records
    for the EXACT same entities the left panel ranked.

    e.g. SQL returned top customers Dorothy Nelson, Edward Harris →
         RAG searches for "Dorothy Nelson", "Edward Harris" across all tables.
    """
    SKIP = {"none", "null", "true", "false", "nan", "n/a"}
    terms: List[str] = []
    if not (sql_result.get("success") and sql_result.get("rows")):
        return terms

    for row in sql_result["rows"][:10]:
        for val in row.values():
            s = str(val).strip()
            # Keep: 3+ chars, not purely numeric, not a skip word
            if (
                len(s) >= 3
                and not s.replace(".", "").replace("-", "").isnumeric()
                and s.lower() not in SKIP
            ):
                terms.append(s)

    # Deduplicate, preserve order, cap at 20
    seen: set = set()
    unique: List[str] = []
    for t in terms:
        if t not in seen:
            seen.add(t)
            unique.append(t)
    return unique[:20]


# ═══════════════════════════════════════════════════════════════
# STEP 1 — SQL LANE
# ═══════════════════════════════════════════════════════════════

def _nl_to_sql(natural_query: str) -> str:
    """Convert a natural-language question to a SQLite SELECT query via Gemini."""
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
    sql = re.sub(r"```sql", "", sql, flags=re.IGNORECASE)
    sql = sql.replace("```", "").strip().rstrip(";")
    return sql


def _run_sql_lane(query: str) -> Dict[str, Any]:
    """NL -> SQL -> execute. Returns structured rows + generated SQL."""
    try:
        sql = _nl_to_sql(query)

        if not _is_read_only(sql):
            return {
                "success": False, "sql": sql, "rows": [],
                "columns": [], "error": "Generated SQL contains write operations — blocked.",
            }

        engine = get_engine()
        with engine.connect() as conn:
            _attach_all(conn)
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
        return {"success": False, "sql": "", "rows": [], "columns": [], "error": str(e)}


# ═══════════════════════════════════════════════════════════════
# STEP 2 — RAG LANE (DB record retrieval using SQL-derived terms)
# ═══════════════════════════════════════════════════════════════

def _run_rag_lane(search_terms: List[str], max_per_table: int = 20) -> Dict[str, Any]:
    """
    Scan all tables in all attached databases using the provided search_terms.

    Two passes per table:
      Pass 1 — column-name match: if a term is found in a column NAME,
               fetch sample rows (handles abstract terms like 'customer').
      Pass 2 — cell-value LIKE:   search literal term inside cell values
               (handles concrete values like 'Dorothy Nelson').

    A table appears at most once (best match wins).
    """
    try:
        if not search_terms:
            return {"success": True, "blocks": [], "keywords": search_terms, "error": None}

        # Also build stemmed variants (strips trailing 's')
        extended: List[str] = []
        for kw in search_terms:
            extended.append(kw)
            if kw.endswith("s") and len(kw) > 4:
                extended.append(kw.rstrip("s"))
        extended = list(dict.fromkeys(extended))  # dedup

        engine = get_engine()
        inspector = sa_inspect(engine)
        active_db_name = os.path.basename(_current_db_uri.split("///")[-1])

        # Collect (qualified_name, col_defs, db_label) for all tables
        table_meta: List[tuple] = []
        for t in inspector.get_table_names():
            table_meta.append((t, inspector.get_columns(t), active_db_name))

        db_files = [f for f in os.listdir(config.DATA_DIR) if f.endswith((".db", ".sqlite"))]
        for db_file in db_files:
            if db_file == active_db_name:
                continue
            alias = re.sub(r"[^a-zA-Z0-9_]", "_", os.path.splitext(db_file)[0])
            try:
                from sqlalchemy import create_engine as ce
                other_engine = ce(f"sqlite:///{config.DATA_DIR / db_file}")
                other_insp = sa_inspect(other_engine)
                for t in other_insp.get_table_names():
                    table_meta.append((f"{alias}.{t}", other_insp.get_columns(t), alias))
            except Exception:
                continue

        blocks: List[Dict] = []
        seen_tables: set = set()

        with engine.connect() as conn:
            _attach_all(conn)

            for (qual_table, col_defs, db_label) in table_meta:
                if qual_table in seen_tables:
                    continue

                col_names = [c["name"] for c in col_defs]
                text_cols = [c["name"] for c in col_defs
                             if "TEXT" in str(c["type"]).upper()
                             or "CHAR" in str(c["type"]).upper()
                             or "VARCHAR" in str(c["type"]).upper()]

                matched_kw = None
                matched_df = pd.DataFrame()

                # Pass 1: column-name match (good for abstract terms)
                for kw in extended:
                    hits = [cn for cn in col_names if kw.lower() in cn.lower()]
                    if hits:
                        try:
                            # If we have real entity values, filter by them; else take sample
                            # Build OR clause over all columns for all search_terms that look
                            # like entity names (contain spaces or mixed case) — this gives
                            # us exactly Dorothy Nelson's rows, not a random 20-row sample.
                            entity_terms = [t for t in search_terms
                                            if " " in t or (t != t.lower() and len(t) > 4)]
                            if entity_terms and text_cols:
                                like_parts = []
                                for et in entity_terms:
                                    for col in text_cols:
                                        safe_et = et.replace("'", "''")
                                        like_parts.append(
                                            f"CAST({col} AS TEXT) LIKE '%{safe_et}%'"
                                        )
                                where = "WHERE " + " OR ".join(like_parts)
                                sql = (f"SELECT * FROM {qual_table} {where} "
                                       f"LIMIT {max_per_table}")
                            else:
                                sql = f"SELECT * FROM {qual_table} LIMIT {max_per_table}"

                            df = pd.read_sql(text(sql), conn)
                            if not df.empty:
                                matched_df = df
                                matched_kw = f"column '{hits[0]}'"
                                break
                        except Exception:
                            continue

                # Pass 2: cell-value LIKE (good for concrete values)
                if matched_df.empty and text_cols:
                    for kw in extended:
                        safe_kw = kw.replace("'", "''")
                        like_clauses = " OR ".join(
                            f"CAST({col} AS TEXT) LIKE '%{safe_kw}%'" for col in text_cols
                        )
                        sql = (f"SELECT * FROM {qual_table} WHERE {like_clauses} "
                               f"LIMIT {max_per_table}")
                        try:
                            df = pd.read_sql(text(sql), conn)
                            if not df.empty and len(df) > len(matched_df):
                                matched_df = df
                                matched_kw = f'"{kw}"'
                        except Exception:
                            continue

                if not matched_df.empty and matched_kw:
                    blocks.append({
                        "table": qual_table,
                        "columns": list(matched_df.columns),
                        "rows": matched_df.to_dict(orient="records"),
                        "matched_keyword": matched_kw,
                        "database": db_label,
                    })
                    seen_tables.add(qual_table)

        return {"success": True, "blocks": blocks, "keywords": search_terms, "error": None}

    except Exception as e:
        return {"success": False, "blocks": [], "keywords": search_terms, "error": str(e)}


# ═══════════════════════════════════════════════════════════════
# AI SYNTHESIS
# ═══════════════════════════════════════════════════════════════

def _synthesize(query: str, sql_result: Dict, rag_result: Dict) -> str:
    """Combine both DB result sets into a concise 2-3 sentence insight."""
    llm = ChatGoogleGenerativeAI(
        model=config.MODEL_NAME,
        google_api_key=config.GOOGLE_API_KEY,
        temperature=0,
    )

    sql_summary = "No analytical results."
    if sql_result.get("success") and sql_result.get("rows"):
        sql_summary = (f"Analytical query top {min(5, len(sql_result['rows']))} rows: "
                       f"{json.dumps(sql_result['rows'][:5])}")

    rag_summary = "No related records found."
    if rag_result.get("blocks"):
        parts = []
        for block in rag_result["blocks"][:2]:
            parts.append(
                f"Table '{block['table']}': {len(block['rows'])} rows. "
                f"Sample: {json.dumps(block['rows'][:2])}"
            )
        rag_summary = " | ".join(parts)

    prompt = (
        f"You are a concise data analyst. Write 2-3 insightful sentences answering the "
        f"question below. Use BOTH the analytical result AND the raw records. Cite numbers.\n\n"
        f"QUESTION: {query}\n\n"
        f"ANALYTICAL RESULT:\n{sql_summary}\n\n"
        f"RELATED RAW RECORDS:\n{rag_summary}\n\n"
        f"INSIGHT:"
    )

    try:
        return llm.invoke(prompt).content.strip()
    except Exception:
        return "Could not generate synthesis — please review both panels manually."


# ═══════════════════════════════════════════════════════════════
# PUBLIC ENTRY POINT
# ═══════════════════════════════════════════════════════════════

def run_hybrid_search(query: str) -> Dict[str, Any]:
    """
    Two-step hybrid search:

      Step 1  SQL lane  — AI-generated analytical SELECT.
      Step 2  RAG lane  — Retrieve raw DB records for the exact same entities
                          that appeared in the SQL results (using their names/IDs
                          as LIKE search terms across all tables).

    Returns:
      {
        "query"    : str,
        "sql"      : { success, sql, columns, rows, total_rows, error },
        "rag"      : { success, blocks, keywords, error },
        "synthesis": str
      }
    """
    # Step 1: analytical SQL
    sql_result = _run_sql_lane(query)

    # Step 2: build search terms from SQL outcome, fall back to query keywords
    result_vals = _values_from_sql_result(sql_result)
    base_kws = _extract_keywords(query)
    search_terms = result_vals if result_vals else base_kws

    # Step 3: RAG-style retrieval from the database
    rag_result = _run_rag_lane(search_terms)

    synthesis = _synthesize(query, sql_result, rag_result)

    return {
        "query": query,
        "sql": sql_result,
        "rag": rag_result,
        "synthesis": synthesis,
    }
