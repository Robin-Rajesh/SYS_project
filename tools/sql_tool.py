"""
sql_tool.py — Self-Correcting, Read-Only SQL Query Tool
========================================================
LangChain Tool that:
  1. Blocks any non-SELECT statement (DROP, DELETE, UPDATE, etc.)
  2. Executes the query against the SQLite sales database
  3. On failure, asks Gemini to correct the SQL and retries (up to 3 times)
  4. Returns "DATA UNAVAILABLE" for empty result sets (no hallucination)
"""

import re
import json
import os
import pandas as pd
from sqlalchemy import create_engine, inspect, text
from langchain_core.tools import tool
from langchain_google_genai import ChatGoogleGenerativeAI

# Import project configuration
import config

# ═══════════════════════════════════════════════════════════════
# 1. DATABASE ENGINE & SCHEMA INTROSPECTION (Dynamic)
# ═══════════════════════════════════════════════════════════════

# Default to the local SQLite DB, but can be overridden by the UI
_current_db_uri = f"sqlite:///{config.DB_PATH}"
_engine = create_engine(_current_db_uri, echo=False)
_schema_cache = None

def set_database_connection(db_uri: str):
    """
    Update the active database connection. 
    Called by the UI when a user switches databases.
    """
    global _current_db_uri, _engine, _schema_cache
    _current_db_uri = db_uri
    _engine = create_engine(_current_db_uri, echo=False)
    _schema_cache = None  # Force schema refresh on next query
    print(f"[SQL Tool] Switched active database connection to: {db_uri}")

def get_engine():
    """Return the currently active SQLAlchemy engine."""
    return _engine

def get_schema() -> str:
    """
    Read (or return cached) schema of the database using SQLAlchemy inspect.
    Injects table names and columns into correction prompts.
    ALSO introspects all other .db files in data/ to support cross-database queries.
    """
    global _schema_cache
    if _schema_cache:
        return _schema_cache
        
    lines = []
    
    # 1. Introspect the PRIMARY database
    engine = get_engine()
    inspector = inspect(engine)
    tables = inspector.get_table_names()
    
    if tables:
        lines.append("--- PRIMARY DATABASE TABLES ---")
        for table_name in tables[:5]:
            columns = inspector.get_columns(table_name)
            lines.append(f"Table: {table_name}")
            lines.append("Columns:")
            for col in columns:
                lines.append(f"  - {col['name']}  ({col['type']})")
            lines.append("")

    # 2. Introspect ALL OTHER databases in data/
    db_files = [f for f in os.listdir(config.DATA_DIR) if f.endswith((".db", ".sqlite"))]
    active_db_name = os.path.basename(_current_db_uri.split("///")[-1])
    
    for db_file in db_files:
        if db_file == active_db_name:
            continue
            
        alias = os.path.splitext(db_file)[0]
        alias = re.sub(r'[^a-zA-Z0-9_]', '_', alias)
        db_path = f"sqlite:///{config.DATA_DIR / db_file}"
        
        try:
            other_engine = create_engine(db_path)
            other_inspector = inspect(other_engine)
            other_tables = other_inspector.get_table_names()
            
            if other_tables:
                lines.append(f"--- ATTACHED DATABASE: {alias} ---")
                for table_name in other_tables[:3]: # Limit to avoid context bloat
                    columns = other_inspector.get_columns(table_name)
                    lines.append(f"Table: {alias}.{table_name}")
                    lines.append("Columns:")
                    for col in columns:
                        lines.append(f"  - {col['name']}  ({col['type']})")
                    lines.append("")
        except Exception:
            continue
        
    _schema_cache = "\n".join(lines)
    return _schema_cache


# ═══════════════════════════════════════════════════════════════
# 2. READ-ONLY GUARDRAIL
# ═══════════════════════════════════════════════════════════════
# A regex pattern that matches dangerous SQL keywords at word
# boundaries. The \b anchor ensures "SELECT" is NOT accidentally
# blocked by a substring match (e.g., "DESELECT" won't trigger it).

_BLOCKED_KEYWORDS = re.compile(
    r"\b(DROP|DELETE|UPDATE|INSERT|ALTER|TRUNCATE|CREATE|REPLACE)\b",
    re.IGNORECASE,
)


def _is_read_only(sql: str) -> bool:
    """Return True if the SQL contains no write/DDL keywords."""
    return _BLOCKED_KEYWORDS.search(sql) is None


# ═══════════════════════════════════════════════════════════════
# 3. SELF-CORRECTING SQL LOOP (uses Gemini to fix bad SQL)
# ═══════════════════════════════════════════════════════════════

def _ask_gemini_to_fix(original_question: str, bad_sql: str,
                       error_msg: str) -> str:
    """
    Send the failed SQL, error message, and DB schema to Gemini
    and ask it to return ONLY the corrected SQL query.
    """
    llm = ChatGoogleGenerativeAI(
        model=config.MODEL_NAME,
        google_api_key=config.GOOGLE_API_KEY,
        temperature=0,
    )
    prompt = f"""You are a SQL expert. A query failed with the error below.
Rewrite ONLY the corrected SQL SELECT query — nothing else, no markdown, no explanation.

DATABASE SCHEMA:
{get_schema()}

ORIGINAL QUESTION: {original_question}

FAILED SQL:
{bad_sql}

ERROR MESSAGE:
{error_msg}

Corrected SQL:"""

    response = llm.invoke(prompt)
    # Strip markdown fences if the model wraps them
    corrected = response.content.strip()
    corrected = corrected.replace("```sql", "").replace("```", "").strip()
    return corrected


# ═══════════════════════════════════════════════════════════════
# 4. LANGCHAIN TOOL DEFINITION
# ═══════════════════════════════════════════════════════════════

@tool
def sql_query_tool(query: str) -> str:
    """Use this to query the connected SQL database.
    Only SELECT statements are allowed.
    Input must be a valid SQL SELECT statement.
    """

    # --- Guardrail: block non-SELECT statements ---
    if not _is_read_only(query):
        return "BLOCKED: Only SELECT statements are permitted."

    last_error = ""
    current_sql = query

    for attempt in range(1, config.MAX_RETRIES + 1):
        try:
            # Execute the SQL and load results into a DataFrame
            with get_engine().connect() as conn:
                # --- AUTO-ATTACH OTHER DATABASES ---
                # Search for all other .db files in the data/ folder and ATTACH them
                # so the agent can perform cross-database JOINs.
                db_files = [f for f in os.listdir(config.DATA_DIR) if f.endswith((".db", ".sqlite"))]
                active_db_name = os.path.basename(_current_db_uri.split("///")[-1])
                
                for db_file in db_files:
                    if db_file != active_db_name:
                        alias = os.path.splitext(db_file)[0]
                        # Sanitize alias (letters and underscores only)
                        alias = re.sub(r'[^a-zA-Z0-9_]', '_', alias)
                        attach_path = str(config.DATA_DIR / db_file).replace("\\", "/")
                        try:
                            conn.execute(text(f"ATTACH DATABASE '{attach_path}' AS {alias}"))
                        except Exception as attach_err:
                            # If it's already attached or fails, we skip it
                            pass

                df = pd.read_sql(text(current_sql), conn)

            # --- No-hallucination guardrail ---
            if df.empty:
                return (
                    "DATA UNAVAILABLE: The query returned no results "
                    "for the given filters."
                )

            # Convert results to a readable string (max 100 rows shown)
            # Also return the raw JSON so the visualizer can ingest it
            result_preview = df.head(100).to_string(index=False)
            result_json = df.head(500).to_dict(orient="records")

            return (
                f"Query executed successfully. Rows returned: {len(df)}\n\n"
                f"{result_preview}\n\n"
                f"[RAW_JSON]{json.dumps(result_json)}[/RAW_JSON]"
            )

        except Exception as e:
            last_error = str(e)
            if attempt < config.MAX_RETRIES:
                # Ask Gemini to fix the query and retry
                current_sql = _ask_gemini_to_fix(query, current_sql, last_error)
                # Safety check: make sure the corrected query is still read-only
                if not _is_read_only(current_sql):
                    return "BLOCKED: Only SELECT statements are permitted."

    # All retries exhausted
    return (
        f"DATA UNAVAILABLE: Query failed after {config.MAX_RETRIES} "
        f"attempts. Last error: {last_error}"
    )
