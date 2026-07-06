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
import difflib
import sqlglot
import sqlglot.expressions as exp
import json
import os
import pandas as pd
from sqlalchemy import create_engine, inspect, text
from langchain_core.tools import tool
from langchain_google_genai import ChatGoogleGenerativeAI, HarmCategory, HarmBlockThreshold

# Import project configuration
import config

# ═══════════════════════════════════════════════════════════════
# 1. DATABASE ENGINE & SCHEMA INTROSPECTION (Dynamic)
# ═══════════════════════════════════════════════════════════════

# Default to the configured DB (Prefer new cloud db over local/old cloud db)
_current_db_uri = config.NEW_SUPABASE_DB_URI or config.DB_URI
_engine = create_engine(_current_db_uri, echo=False, pool_pre_ping=True, pool_recycle=120, pool_size=1, max_overflow=0)
_schema_cache = None
_db_index_cache = None

def set_database_connection(db_uri: str):
    """
    Update the active database connection. 
    Called by the UI when a user switches databases.
    """
    global _current_db_uri, _engine, _schema_cache, _db_index_cache
    _current_db_uri = db_uri
    _engine = create_engine(_current_db_uri, echo=False, pool_pre_ping=True, pool_recycle=120, pool_size=1, max_overflow=0)
    _schema_cache = None       # Force schema refresh on next query
    _db_index_cache = None     # Force index refresh on next query
    print(f"[SQL Tool] Switched active database connection to: {db_uri}")

def get_engine():
    """Return the currently active SQLAlchemy engine."""
    return _engine

def get_schema() -> str:
    """
    Returns a 'Core Schema' of the first 5 tables.
    Used for the initial system prompt to give the AI context on the main tables.
    """
    global _schema_cache
    if _schema_cache:
        return _schema_cache
        
    lines = ["--- CORE DATABASE TABLES ---"]
    engine = get_engine()
    inspector = inspect(engine)
    tables = inspector.get_table_names()
    
    for table_name in tables[:20]:
        columns = inspector.get_columns(table_name)
        pk = inspector.get_pk_constraint(table_name)
        fks = inspector.get_foreign_keys(table_name)
        
        lines.append(f"CREATE TABLE {table_name} (")
        col_lines = []
        for col in columns:
            col_lines.append(f"    {col['name']} {col['type']}")
            
        if pk and pk.get('constrained_columns'):
            pk_cols = ", ".join(pk['constrained_columns'])
            col_lines.append(f"    PRIMARY KEY ({pk_cols})")
            
        for fk in fks:
            fk_cols = ", ".join(fk['constrained_columns'])
            ref_table = fk['referred_table']
            ref_cols = ", ".join(fk['referred_columns'])
            col_lines.append(f"    FOREIGN KEY ({fk_cols}) REFERENCES {ref_table}({ref_cols})")
            
        lines.append(",\n".join(col_lines))
        lines.append(");\n")

    _schema_cache = "\n".join(lines)
    return _schema_cache

def get_db_index() -> str:
    """
    Returns a simple list of ALL table names in all connected databases.
    This lets the AI know what exists without dumping 1000s of columns.
    """
    global _db_index_cache
    if _db_index_cache:
        return _db_index_cache

    engine = get_engine()
    inspector = inspect(engine)
    primary = inspector.get_table_names()
    
    lines = [f"TOTAL TABLES: {len(primary)}", "TABLE NAME INDEX (PRIMARY):", ", ".join(primary)]
    
    # Only scan for additional local .db files when NOT in cloud mode.
    # In cloud mode, _current_db_uri is a postgresql:// URL and this block
    # would incorrectly mix local SQLite table names into the cloud schema.
    if not config.IS_CLOUD:
        db_files = [f for f in os.listdir(config.DATA_DIR) if f.endswith((".db", ".sqlite"))]
        active_db_name = os.path.basename(_current_db_uri.split("///")[-1])
        for db_file in db_files:
            if db_file == active_db_name: continue
            alias = os.path.splitext(db_file)[0]
            alias = re.sub(r'[^a-zA-Z0-9_]', '_', alias)
            try:
                other_engine = create_engine(f"sqlite:///{config.DATA_DIR / db_file}")
                other_insp = inspect(other_engine)
                other_tabs = other_insp.get_table_names()
                if other_tabs:
                    lines.append(f"\nTABLE NAME INDEX ({alias}):")
                    lines.append(", ".join([f"{alias}.{t}" for t in other_tabs]))
            except Exception: pass
        
    _db_index_cache = "\n".join(lines)
    return _db_index_cache


# ═══════════════════════════════════════════════════════════════
# 2. SCHEMA INSPECTION TOOL
# ═══════════════════════════════════════════════════════════════

from langchain_core.tools import tool  # already imported at top — do NOT re-import from langchain.tools

@tool
def inspect_table_columns(table_name: str) -> str:
    """
    Returns the full list of columns and types for a specific table.
    Use this if you see a table in the INDEX that you need to query, 
    but don't have its columns in the CORE SCHEMA.
    """
    try:
        engine = get_engine()
        # Handle cross-db aliases (e.g. 'other_db.table_name')
        if "." in table_name:
            alias, real_name = table_name.split(".", 1)
            # Find the actual .db file for this alias
            db_files = [f for f in os.listdir(config.DATA_DIR) if f.endswith((".db", ".sqlite"))]
            target_path = None
            for db_file in db_files:
                curr_alias = re.sub(r'[^a-zA-Z0-9_]', '_', os.path.splitext(db_file)[0])
                if curr_alias == alias:
                    target_path = config.DATA_DIR / db_file
                    break
            if not target_path:
                return f"ERROR: Database alias '{alias}' not found."
            engine = create_engine(f"sqlite:///{target_path}")
            table_name = real_name

        inspector = inspect(engine)
        if table_name not in inspector.get_table_names():
            return f"ERROR: Table '{table_name}' does not exist."
            
        columns = inspector.get_columns(table_name)
        res = [f"SCHEMA FOR TABLE: {table_name}", "Columns:"]
        for col in columns:
            res.append(f"  - {col['name']} ({col['type']})")
        return "\n".join(res)
    except Exception as e:
        return f"ERROR: {str(e)}"


# ═══════════════════════════════════════════════════════════════
# 2. READ-ONLY GUARDRAIL
# ═══════════════════════════════════════════════════════════════
# A regex pattern that matches dangerous SQL keywords at word
# boundaries. The \b anchor ensures "SELECT" is NOT accidentally
# blocked by a substring match (e.g., "DESELECT" won't trigger it).

# Only block write/DDL keywords when they are the FIRST meaningful token
# in the statement (prevents false positives from schema DDL in comments/context).
_BLOCKED_KEYWORDS = re.compile(
    r"^\s*(DROP|DELETE|UPDATE|INSERT|ALTER|TRUNCATE|CREATE|REPLACE)\b",
    re.IGNORECASE | re.MULTILINE,
)


def _is_read_only(sql: str) -> bool:
    """Return True if the SQL contains no write/DDL keywords as first tokens."""
    # Strip out CTE names and subqueries before checking
    # Only check the very first keyword of the full statement
    stripped = sql.strip()
    first_token = re.match(r'^(\w+)', stripped)
    if first_token:
        return first_token.group(1).upper() not in (
            'DROP', 'DELETE', 'UPDATE', 'INSERT', 'ALTER', 'TRUNCATE', 'CREATE', 'REPLACE'
        )
    return True


# ═══════════════════════════════════════════════════════════════
# 3. DETERMINISTIC SQL COLUMN VALIDATOR
# ═══════════════════════════════════════════════════════════════
# Uses sqlglot to parse the AI-generated SQL into an AST, then
# cross-references every column reference against the real database
# schema (via SQLAlchemy). Hallucinated column names are auto-corrected
# using fuzzy matching (difflib) BEFORE the query reaches Supabase.
# This is 100% deterministic Python code — no LLM involved.
# ═══════════════════════════════════════════════════════════════

# Cache of real column names per table: {table_name: [col1, col2, ...]}
_real_columns_cache: dict = {}

# Explicit abbreviation/synonym map for common AI hallucinations.
# These are checked FIRST before fuzzy matching.
# Format: {hallucinated_name: real_name}
_COLUMN_SYNONYMS: dict[str, str] = {
    "quantity":      "qty",
    "amount":        "refund",      # in returns table
    "product_name":  None,          # Does not exist — block it
    "name":          None,          # Too ambiguous — block it
    "total":         None,          # Computed, not a stored column
}


def _get_real_columns(table_name: str) -> list[str]:
    """Fetch and cache the real column names for a table from the DB."""
    if table_name not in _real_columns_cache:
        try:
            inspector = inspect(get_engine())
            cols = inspector.get_columns(table_name)
            _real_columns_cache[table_name] = [c['name'] for c in cols]
        except Exception:
            _real_columns_cache[table_name] = []  # Table not found
    return _real_columns_cache[table_name]


def _validate_and_fix_sql(sql: str) -> tuple[str, list[str]]:
    """
    Parse the AI-generated SQL with sqlglot, extract all column references,
    check each against the real database schema, and auto-correct any
    hallucinated column names using fuzzy matching.

    Returns:
        (corrected_sql, list_of_corrections_made)
    """
    corrections = []

    try:
        # Parse the SQL into an AST (Abstract Syntax Tree)
        ast = sqlglot.parse_one(sql, dialect="postgres")
    except Exception:
        # If sqlglot can't parse it at all, return as-is and let Supabase handle it
        return sql, []

    # --- Step 1: Build a map of alias -> real table name ---
    # e.g., "oi" -> "order_items", "p" -> "products"
    alias_to_table: dict[str, str] = {}

    # Walk the AST to find all table references (FROM, JOIN)
    for table_node in ast.find_all(exp.Table):
        real_name = table_node.name
        alias = table_node.alias or real_name
        if real_name:
            alias_to_table[alias.lower()] = real_name.lower()
            alias_to_table[real_name.lower()] = real_name.lower()

    if not alias_to_table:
        return sql, []  # No tables found, nothing to validate

    # --- Step 2: Check every Column node in the AST ---
    for col_node in ast.find_all(exp.Column):
        col_name = col_node.name
        table_alias = col_node.table  # e.g., "oi" in "oi.qty"

        if not col_name or not table_alias:
            continue  # Skip unqualified columns (can't validate without table context)

        # Resolve alias to real table name
        real_table = alias_to_table.get(table_alias.lower())
        if not real_table:
            continue  # Unknown alias, skip

        # Get actual columns from the database
        real_cols = _get_real_columns(real_table)
        if not real_cols:
            continue  # Table not found in DB, let Supabase handle it

        # Check if the column exists (case-insensitive)
        real_cols_lower = [c.lower() for c in real_cols]
        if col_name.lower() in real_cols_lower:
            continue  # Column is correct — no action needed

        # --- Explicit Synonym Check ---
        # Did the AI hallucinate a known abbreviation (e.g. 'quantity')?
        if col_name.lower() in _COLUMN_SYNONYMS:
            mapped_name = _COLUMN_SYNONYMS[col_name.lower()]
            if mapped_name and mapped_name.lower() in real_cols_lower:
                # Synonym exists in this table — auto-correct it
                corrected_name = real_cols[real_cols_lower.index(mapped_name.lower())]
                corrections.append(
                    f"[Validator] Syn-corrected: {table_alias}.{col_name} -> {table_alias}.{corrected_name} (table: {real_table})"
                )
                col_node.set("this", exp.to_identifier(corrected_name))
                continue
            elif mapped_name is None:
                # It's an explicitly blocked column name (like product_name)
                # Let it fall through to generate a warning/error
                pass

        # --- Fuzzy Match Check ---
        # Column does NOT exist and no synonym matches — try fuzzy matching
        matches = difflib.get_close_matches(
            col_name.lower(),
            real_cols_lower,
            n=1,
            cutoff=0.85,  # 85% similarity threshold (strict to prevent bad guesses)
        )

        if matches:
            # Find the original casing of the matched column
            corrected_name = real_cols[real_cols_lower.index(matches[0])]
            corrections.append(
                f"[Validator] Fuzzy-corrected: {table_alias}.{col_name} -> {table_alias}.{corrected_name} (table: {real_table})"
            )
            # Rewrite the column name in the AST node
            col_node.set("this", exp.to_identifier(corrected_name))
        else:
            # No close match found — log but don't crash, let Supabase give the real error
            corrections.append(
                f"[Validator] WARNING: '{col_name}' not found in '{real_table}'. "
                f"Valid columns: {real_cols}"
            )

    # --- Step 3: Re-serialize the (possibly corrected) AST back to SQL ---
    try:
        corrected_sql = ast.sql(dialect="postgres")
        return corrected_sql, corrections
    except Exception:
        # If re-serialization fails, return original
        return sql, corrections


# ═══════════════════════════════════════════════════════════════
# 4. SELF-CORRECTING SQL LOOP (uses Gemini to fix bad SQL)
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
        safety_settings={
            HarmCategory.HARM_CATEGORY_HARASSMENT: HarmBlockThreshold.BLOCK_NONE,
            HarmCategory.HARM_CATEGORY_HATE_SPEECH: HarmBlockThreshold.BLOCK_NONE,
            HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT: HarmBlockThreshold.BLOCK_NONE,
            HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT: HarmBlockThreshold.BLOCK_NONE,
        }
    )
    prompt = f"""You are a SQL expert. A query failed with the error below.
Rewrite ONLY the corrected SQL SELECT query — nothing else, no markdown, no explanation.

CRITICAL RULES:
1. ONLY utilize columns and tables defined in the provided schema. Do NOT hallucinate.
2. Resolve any missing column errors by reviewing the schema and choosing the correct, existing name.
3. If string matching caused the error or data absence, you MUST use `LOWER(column) LIKE LOWER('%value%')`.
4. NO PRODUCT NAME COLUMN: The products table does NOT have a product_name or name column. It only has product_id, category_id, supplier_id, and price. Use category_name from categories.
5. COLUMN ALIAS RULES (CRITICAL): In the order_items table, the column for quantity is EXACTLY `qty`. DO NOT use `quantity`. Doing so will cause a fatal error.

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
# 4. PROGRAMMATIC SUMMARY (deterministic, LLM-free)
# ═══════════════════════════════════════════════════════════════

# Global so api.py can access the last real DataFrame result — zero hallucination possible.
last_query_dataframe: pd.DataFrame = pd.DataFrame()
last_executed_sqls: list[str] = []


def generate_programmatic_summary(df: pd.DataFrame) -> str:
    """
    Deterministic, LLM-free summary of query results.
    Every number here comes directly from the DataFrame — zero hallucination possible.
    """
    if df.empty:
        return "⚠️ Query returned 0 rows. No data found."

    lines = [f"**Query returned {len(df):,} rows with {len(df.columns)} columns.**\n"]

    for col in df.columns:
        if pd.api.types.is_numeric_dtype(df[col]):
            lines.append(
                f"- **{col}**: "
                f"Total = {df[col].sum():,.2f} | "
                f"Avg = {df[col].mean():,.2f} | "
                f"Min = {df[col].min():,.2f} | "
                f"Max = {df[col].max():,.2f}"
            )
        else:
            unique_count = df[col].nunique()
            lines.append(f"- **{col}**: {unique_count:,} unique values")

    return "\n".join(lines)


# ═══════════════════════════════════════════════════════════════
# 5. LANGCHAIN TOOL DEFINITION
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
                # so the agent can perform cross-database JOINs (SQLite ONLY).
                if not config.IS_CLOUD:
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

                # --- DETERMINISTIC VALIDATOR: fix hallucinated columns before hitting DB ---
                validated_sql, auto_corrections = _validate_and_fix_sql(current_sql)
                if auto_corrections:
                    for msg in auto_corrections:
                        print(msg)
                    current_sql = validated_sql

                df = pd.read_sql(text(current_sql), conn)

            global last_query_dataframe, last_executed_sqls
            last_query_dataframe = df  # Store for api.py to inject as ground truth
            last_executed_sqls.append(current_sql)

            # --- No-hallucination guardrail ---
            if df.empty:
                return (
                    "DATA UNAVAILABLE: The query returned no results for the given filters. "
                    "[AGENT INSTRUCTION] Explain to the user why no data was found (e.g. the filter value may not exist, "
                    "or the column/table may not contain the expected data), then suggest 2-3 alternative questions "
                    "they could ask instead that would return useful results from the available data."
                )

            # Build programmatic summary (deterministic — no LLM involved)
            programmatic_summary = generate_programmatic_summary(df)

            # Cap preview at 50 rows; note overflow if there are more
            result_preview = df.head(50).to_string(index=False)
            overflow_note = ""
            if len(df) > 50:
                overflow_note = f"\n(Showing 50 of {len(df):,} rows)"

            return (
                f"Query executed successfully. Rows returned: {len(df)}\n"
                f"Executed SQL: ```sql\n{current_sql}\n```\n\n"
                f"⚠️ CRITICAL: THE FOLLOWING IS THE ACTUAL DATABASE RESULT.\n"
                f"Your ONLY job is to briefly explain what was searched and which tables were used.\n"
                f"Do NOT restate, rephrase, or repeat any numbers from this table.\n"
                f"=== ACTUAL DATA FROM DATABASE (verbatim) ===\n"
                f"{result_preview}{overflow_note}\n"
                f"=== END OF ACTUAL DATA ===\n\n"
                f"PROGRAMMATIC SUMMARY (auto-generated — do NOT repeat these numbers in your response):\n"
                f"{programmatic_summary}"
            )

        except Exception as e:
            last_error = str(e)
            if attempt < config.MAX_RETRIES:
                print(f"[SELF-HEAL] Attempt {attempt} for query: {query[:100]}...")
                # Ask Gemini to fix the query and retry
                current_sql = _ask_gemini_to_fix(query, current_sql, last_error)
                # Safety check: make sure the corrected query is still read-only
                if not _is_read_only(current_sql):
                    return "BLOCKED: Only SELECT statements are permitted."

    # All retries exhausted
    return (
        f"DATA UNAVAILABLE: Query failed after {config.MAX_RETRIES} attempts. "
        f"Last error: {last_error}. "
        f"[AGENT INSTRUCTION] Explain to the user that the query could not be completed and why, "
        f"then suggest 2-3 alternative questions they could ask instead that would return useful results."
    )
