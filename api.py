"""
api.py — FastAPI Backend for Enterprise Data Analyst AI
========================================================
Drop this file in your SYS_project root and run:
    pip install fastapi uvicorn sse-starlette python-multipart
    uvicorn api:app --reload --port 8000

All existing agent.py / tools stay UNTOUCHED.
"""

import os
import json
import importlib.util
import subprocess
import smtplib
from email.message import EmailMessage
from typing import Optional, AsyncGenerator

import pandas as pd
from fastapi import FastAPI, HTTPException, UploadFile, File, Form
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from sqlalchemy import create_engine, inspect, text

from contextlib import asynccontextmanager
import config
from agent import stream_agent, run_agent, clear_memory
from tools.sql_tool import set_database_connection, get_engine
from tools.rag_tool import _retrieve, _build_and_get_vector_store

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup actions
    print("[Lifespan Startup] Running database and schema auto-sync...")
    try:
        from scripts.sync_schema import sync_schema
        from scripts.embed_schema import sync_embeddings
        sync_schema()
        sync_embeddings()
        print("[Lifespan Startup] Schema auto-sync complete!")
    except Exception as e:
        print(f"[Lifespan Startup] Error during startup schema auto-sync: {e}")
    yield

# ─────────────────────────────────────────────
app = FastAPI(title="Enterprise Data Analyst AI", version="1.0.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ═══════════════════════════════════════════════
# MODELS
# ═══════════════════════════════════════════════

class ChatRequest(BaseModel):
    message: str

class PolicyRequest(BaseModel):
    query: str

class DbConnectRequest(BaseModel):
    db_filename: str

class ScheduleRequest(BaseModel):
    time_str: str
    recipient_email: str
    enabled: bool

class EmailReportRequest(BaseModel):
    recipient_email: str
    html_content: str

class SchemaRelationship(BaseModel):
    source_db: str
    source_table: str
    source_column: str
    target_db: str
    target_table: str
    target_column: str
    type: str

class TableMetaOut(BaseModel):
    table_name: str
    description: str
    updated_at: Optional[str] = None

# ═══════════════════════════════════════════════
# 1. DATABASE
# ═══════════════════════════════════════════════

@app.get("/api/databases")
def list_databases():
    if config.IS_CLOUD:
        return {"databases": ["Supabase PostgreSQL (Cloud)"], "active": "Supabase PostgreSQL (Cloud)"}
    files = [f for f in os.listdir(config.DATA_DIR) if f.endswith((".db", ".sqlite")) and f != "cloud_postgres.db"]
    return {"databases": files, "active": str(config.DB_PATH)}

@app.post("/api/databases/connect")
def connect_database(req: DbConnectRequest):
    if config.IS_CLOUD:
        return {"success": True, "uri": config.DB_URI}
        
    uri = f"sqlite:///{config.DATA_DIR / req.db_filename}"
    try:
        set_database_connection(uri)
        clear_memory()
        global _cached_general_suggestions
        _cached_general_suggestions = None  # Force fresh suggestions for new DB
        return {"success": True, "uri": uri}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.get("/api/tables")
def list_tables(db_filename: Optional[str] = None):
    if config.IS_CLOUD:
        engine = create_engine(config.DB_URI, pool_pre_ping=True, pool_recycle=120, pool_size=1, max_overflow=0)
    elif db_filename:
        engine = create_engine(f"sqlite:///{config.DATA_DIR / db_filename}")
    else:
        engine = get_engine()
    tables = inspect(engine).get_table_names()
    return {"tables": tables}

@app.get("/api/tables/{table_name}/columns")
def get_columns(table_name: str, db_filename: Optional[str] = None):
    try:
        from sqlalchemy import create_engine, inspect
        if config.IS_CLOUD:
            engine = create_engine(config.DB_URI, pool_pre_ping=True, pool_recycle=120, pool_size=1, max_overflow=0)
        elif db_filename:
            engine = create_engine(f"sqlite:///{config.DATA_DIR / db_filename}")
        else:
            engine = get_engine()
        cols = [{"name": c["name"], "type": str(c["type"])}
                for c in inspect(engine).get_columns(table_name)]
        return {"columns": cols}
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/tables/{table_name}/data")
def get_table_data(
    table_name: str,
    page: int = 1,
    page_size: int = 10,
    filter_col: Optional[str] = None,
    filter_val: Optional[str] = None,
    sort_col: Optional[str] = None,
    sort_order: str = "ASC",
    global_search: Optional[str] = None
):
    engine = get_engine()
    from sqlalchemy import text
    query_params = {}
    
    where_clauses = []
    
    # Build Global Search clause
    if global_search:
        # Search across all text columns, case-insensitive and quoting column names for Postgres
        cols = [c["name"] for c in inspect(engine).get_columns(table_name)]
        like_clauses = " OR ".join([f"LOWER(CAST(\"{col}\" AS TEXT)) LIKE LOWER(:glob_val)" for col in cols])
        where_clauses.append(f"({like_clauses})")
        query_params["glob_val"] = f"%{global_search}%"
        
    # Build specific column filter clause
    if filter_col and filter_col != "None" and filter_val:
        where_clauses.append(f"LOWER(CAST(\"{filter_col}\" AS TEXT)) LIKE LOWER(:filt_val)")
        query_params["filt_val"] = f"%{filter_val}%"
        
    where = ""
    if where_clauses:
        where = "WHERE " + " AND ".join(where_clauses)
        
    order = f"ORDER BY \"{sort_col}\" {sort_order}" if sort_col and sort_col != "None" else ""
    offset = (page - 1) * page_size
    
    try:
        count_query = text(f"SELECT COUNT(*) as c FROM \"{table_name}\" {where}")
        count_df = pd.read_sql(count_query, engine, params=query_params)
        total = int(count_df.iloc[0, 0])
    except Exception as e:
        print("Count err:", e)
        total = 0
        
    try:
        data_query = text(f"SELECT * FROM \"{table_name}\" {where} {order} LIMIT {page_size} OFFSET {offset}")
        df = pd.read_sql(data_query, engine, params=query_params)
    except Exception as e:
        print("Data err:", e)
        df = pd.DataFrame()
        
    return {
        "rows": df.to_dict(orient="records"),
        "total": total,
        "page": page,
        "page_size": page_size,
        "total_pages": max(1, (total + page_size - 1) // page_size)
    }

@app.post("/api/tables/{table_name}/ai-scan")
def ai_data_quality_scan(table_name: str):
    from agent import llm
    engine = get_engine()
    schema_info = [(c["name"], str(c["type"])) for c in inspect(engine).get_columns(table_name)]
    from sqlalchemy import text
    df = pd.read_sql(text(f"SELECT * FROM \"{table_name}\" LIMIT 10"), engine)
    prompt = f"""You are an AI Data Quality Engineer. Analyze the table schema and data sample below.
Identify exactly 2 data quality issues. Return ONLY a valid JSON array — no markdown, no explanation outside the JSON.

Each object in the array must have exactly these keys:
  "title"          – short issue name (5 words max)
  "severity"       – one of: "high", "medium", "low"
  "description"    – what the problem is (1–2 sentences, plain English)
  "recommendation" – concrete fix the developer should apply (1 sentence)
  "affected"       – which column(s) are impacted (comma-separated names or "All columns")

TABLE SCHEMA:
{schema_info}

DATA SAMPLE (first 10 rows):
{df.head(10).to_string(index=False)}

Return only the JSON array."""

    result = llm.invoke(prompt)
    raw = result.content.strip().replace("```json", "").replace("```", "").strip()
    try:
        issues = json.loads(raw)
        if not isinstance(issues, list):
            raise ValueError("not a list")
    except Exception:
        # Fallback: wrap the raw text in a single structured item
        issues = [{
            "title": "Analysis Result",
            "severity": "medium",
            "description": raw[:400],
            "recommendation": "Review the findings above and consult your DBA.",
            "affected": "See description"
        }]
    return {"issues": issues}

# ═══════════════════════════════════════════════
# 2. AGENT CHAT (SSE streaming)
# ═══════════════════════════════════════════════

@app.post("/api/chat/stream")
async def chat_stream(req: ChatRequest):
    async def generate() -> AsyncGenerator[str, None]:
        import tools.sql_tool as _sql_mod

        final_response = ""
        plotly_json = None
        all_sql_queries: list[str] = []  # track every SQL call in order
        total_tokens_used = 0
        last_tool_result = ""
        all_tool_results: list[str] = []  # all raw tool outputs in order

        # Reset the shared DataFrame before this request so a stale result
        # from a prior request cannot leak through if the agent skips SQL.
        _sql_mod.last_query_dataframe = pd.DataFrame()
        _sql_mod.last_executed_sqls.clear()

        for step in stream_agent(req.message):
            if "agent" in step:
                msgs = step["agent"].get("messages", [])
                if msgs:
                    msg = msgs[-1]

                    # --- Parse tool calls (does NOT clear content) ---
                    if getattr(msg, "tool_calls", None):
                        for tc in msg.tool_calls:
                            event = {"type": "tool_call", "name": tc["name"], "args": str(tc["args"])}
                            yield f"data: {json.dumps(event)}\n\n"

                            try:
                                args_val = tc.get("args", {})
                                if isinstance(args_val, str):
                                    try:
                                        args_dict = json.loads(args_val)
                                    except Exception:
                                        import ast
                                        try:
                                            args_dict = ast.literal_eval(args_val)
                                        except Exception:
                                            args_dict = {}
                                else:
                                    args_dict = args_val

                                if tc["name"] == "sql_query_tool":
                                    sql_q = (
                                        args_dict.get("query") or
                                        args_dict.get("sql") or
                                        args_dict.get("input") or
                                        args_dict.get("sql_query")
                                    )
                                    if not sql_q and args_dict:
                                        sql_q = list(args_dict.values())[0]
                                    if sql_q:
                                        all_sql_queries.append(sql_q)
                                        print(f"\n🔍 [SQL #{len(all_sql_queries)}]\n{sql_q}\n")

                                if tc["name"] == "visualization_tool":
                                    from tools.visualizer_tool import _create_chart

                                    if "input_json" in args_dict:
                                        in_json = args_dict["input_json"]
                                        payload = json.loads(in_json) if isinstance(in_json, str) else in_json
                                    else:
                                        payload = args_dict

                                    # Use the real DataFrame from memory, ignore whatever the LLM tried to pass
                                    df = _sql_mod.last_query_dataframe
                                    if df is not None and not df.empty:
                                        fig = _create_chart(
                                            df,
                                            payload.get("chart_type", "bar"),
                                            payload.get("x_column", ""),
                                            payload.get("y_column", ""),
                                            payload.get("title", ""),
                                            payload.get("color_column", "")
                                        )
                                        plotly_json = fig.to_json()
                            except Exception as e:
                                import traceback
                                print("❌ TOOL PARSE ERROR:", e)
                                traceback.print_exc()

                    # --- Extract text content from this agent message ---
                    content = ""
                    if hasattr(msg, "content"):
                        if isinstance(msg.content, str):
                            content = msg.content
                        elif isinstance(msg.content, list):
                            content = " ".join(
                                m.get("text", "") if isinstance(m, dict) else str(m)
                                for m in msg.content
                            )

                    # --- Token tracking ---
                    if hasattr(msg, "usage_metadata") and msg.usage_metadata:
                        total_tokens_used += msg.usage_metadata.get("total_tokens", 0)
                        print(
                            f"\n📊 [TOKEN USAGE] Input: {msg.usage_metadata.get('input_tokens', 0)} "
                            f"| Output: {msg.usage_metadata.get('output_tokens', 0)} "
                            f"| Total Current Step: {msg.usage_metadata.get('total_tokens', 0)}\n"
                        )

                    # Only update final_response when the message has actual text
                    # and is not a pure tool-call message (those have empty text content).
                    if content.strip() and not getattr(msg, "tool_calls", None):
                        final_response = content

            elif "tools" in step:
                msgs = step["tools"].get("messages", [])
                if msgs:
                    last_tool_result = msgs[-1].content
                    all_tool_results.append(last_tool_result)
                    yield f"data: {json.dumps({'type': 'tool_result', 'content': last_tool_result[:500]})}\n\n"

            elif "error" in step:
                yield f"data: {json.dumps({'type': 'error', 'content': step['error']})}\n\n"

        # ── Stream finished — begin post-processing ──────────────────────────

        # Fallback: if the agent emitted no final text, surface the last tool result.
        if not final_response.strip():
            if last_tool_result.strip():
                final_response = last_tool_result
            else:
                final_response = "The agent completed the task but produced no text output. Please try rephrasing your question."

        # ── GROUND-TRUTH OVERRIDE ────────────────────────────────────────────
        # last_query_dataframe holds the real result set from the last SQL call.
        # Case A: last query empty + DATA UNAVAILABLE seen → hard override.
        # Case B: last query has rows → insert verified table right after narrative
        #         then SQL block at the very bottom (no visual gap between text & table).
        # Case C: no SQL at all → pass narrative through unchanged.

        df_result = _sql_mod.last_query_dataframe
        actual_sqls = _sql_mod.last_executed_sqls
        
        is_zero_row = (
            all_sql_queries                                           # SQL was called
            and df_result.empty                                       # tool returned nothing
            and any("DATA UNAVAILABLE" in r for r in all_tool_results)  # guard string present
        )

        # Build the SQL block (appended last so it doesn't break up narrative + table)
        sql_block_str = ""
        if actual_sqls and "```sql" not in final_response:
            if len(actual_sqls) == 1:
                sql_block_str = f"\n\n```sql\n{actual_sqls[0]}\n```"
            else:
                combined = "\n\n".join(
                    f"-- Query {i+1}\n{q}" for i, q in enumerate(actual_sqls)
                )
                sql_block_str = f"\n\n```sql\n{combined}\n```"

        if is_zero_row:
            # Case A — all queries returned 0 rows
            print("\u26a0\ufe0f  [HALLUCINATION GUARD] SQL returned 0 rows. LLM response overridden.")
            unavail_msg = next(
                (r for r in all_tool_results if "DATA UNAVAILABLE" in r),
                "DATA UNAVAILABLE: The query returned no results."
            )
            user_msg = unavail_msg.split("[AGENT INSTRUCTION]")[0].strip()
            final_response = (
                f"**No matching data found in the database.**\n\n"
                f"The SQL {'query was' if len(actual_sqls) == 1 else f'{len(actual_sqls)} queries were'} "
                f"executed and returned **0 rows**. "
                f"This means the condition you asked about does not exist in the current dataset.\n\n"
                f"> {user_msg}\n\n"
                f"You may want to rephrase the question, check for a related condition, "
                f"or ask what data *is* available in the relevant tables."
            )
            final_response += sql_block_str

        elif not df_result.empty:
            # Case B — append verified table immediately after narrative (no SQL in between)
            try:
                table_section = df_result.head(50).to_markdown(index=False)
                overflow_note = ""
                if len(df_result) > 50:
                    overflow_note = f"\n*Showing 50 of {len(df_result):,} rows.*"

                verified_block = (
                    f"\n\n**Results** ({len(df_result):,} row{'s' if len(df_result) != 1 else ''})\n\n"
                    f"{table_section}{overflow_note}\n\n"
                    f"{_sql_mod.generate_programmatic_summary(df_result)}"
                )
                final_response += verified_block + sql_block_str
                print(f"   \u2192 Verified block appended ({min(len(df_result), 50)} of {len(df_result)} rows).")
            except Exception as _block_err:
                print(f"\u274c [VERIFIED BLOCK ERROR] {_block_err}")
                import traceback; traceback.print_exc()
                final_response += sql_block_str  # still show SQL even if table failed

        else:
            # Case C/D: either no SQL at all, or the agent wrote SQL as text without calling the tool.
            # Case D: detect a sql block in the response and auto-execute it so the user gets real data.
            if not actual_sqls and "```sql" in final_response:
                import re as _re
                sql_match = _re.search(r"```sql\n([\s\S]*?)\n```", final_response, _re.IGNORECASE)
                if sql_match:
                    extracted_sql = sql_match.group(1).strip()
                    print(f"\n⚡ [CASE D] Agent skipped tool call — auto-executing extracted SQL:\n{extracted_sql}\n")
                    try:
                        from tools.sql_tool import _is_read_only, _validate_and_fix_sql
                        from sqlalchemy import text as _text
                        import pandas as _pd
                        if _is_read_only(extracted_sql):
                            validated_sql, _ = _validate_and_fix_sql(extracted_sql)
                            with get_engine().connect() as _conn:
                                auto_df = _pd.read_sql(_text(validated_sql), _conn)
                            if not auto_df.empty:
                                table_section = auto_df.head(50).to_markdown(index=False)
                                overflow_note = f"\n*Showing 50 of {len(auto_df):,} rows.*" if len(auto_df) > 50 else ""
                                verified_block = (
                                    f"\n\n**Results** ({len(auto_df):,} row{'s' if len(auto_df) != 1 else ''})\n\n"
                                    f"{table_section}{overflow_note}\n\n"
                                    f"{_sql_mod.generate_programmatic_summary(auto_df)}"
                                )
                                final_response += verified_block
                                print(f"   → Case D: auto-injected {min(len(auto_df), 50)} of {len(auto_df)} rows.")
                    except Exception as _case_d_err:
                        print(f"❌ [CASE D ERROR] {_case_d_err}")
            else:
                final_response += sql_block_str


        # Reset for the next request
        _sql_mod.last_query_dataframe = pd.DataFrame()
        _sql_mod.last_executed_sqls.clear()
        # ────────────────────────────────────────────────────────────────────

        # Log summary to terminal for debugging
        print(f"\n📋 [AGENT SUMMARY] {len(actual_sqls)} SQL query/queries executed for: '{req.message[:80]}'")

        response_event = {"type": "response", "content": final_response}
        if plotly_json:
            response_event["plotly_json"] = plotly_json

        # Optional: send token count to frontend so it can be rendered
        if total_tokens_used > 0:
            response_event["tokens"] = total_tokens_used

        yield f"data: {json.dumps(response_event)}\n\n"
        yield 'data: {"type": "done"}\n\n'

    return StreamingResponse(generate(), media_type="text/event-stream")

@app.post("/api/chat/clear")
def clear_chat():
    clear_memory()
    return {"success": True}

_cached_general_suggestions = None

@app.get("/api/chat/suggestions")
async def get_chat_suggestions(context: str = None):
    """
    Generates 4 dynamic business questions using the LLM.
    If 'context' is provided (e.g., the last user message), it generates
    follow-up questions. Otherwise, it generates general 
    exploratory questions based on the live database schema.
    """
    global _cached_general_suggestions
    from tools.sql_tool import get_schema, get_db_index
    from agent import llm
    
    # Return cache only if no context — regenerate fresh on each startup
    if not context and _cached_general_suggestions:
        return {"suggestions": _cached_general_suggestions}

    schema = get_schema()
    db_index = get_db_index()   # Full list of ALL table names in the DB

    if context:
        prompt = f"""
You are a Senior Data Analyst. The user just asked: "{context}"
Based on our database schema below, generate exactly 4 highly relevant FOLLOW-UP 
business questions the user should ask next. Focus on drilling deeper into the data or finding anomalies.
CRITICAL: Keep EACH question very short and punchy (under 10 words).
Return ONLY a valid JSON array of 4 strings. No markdown formatting or extra text.

CORE SCHEMA:
{schema}
"""
    else:
        prompt = f"""
You are a Senior Data Analyst. The database below contains these tables.
Generate exactly 4 highly insightful, distinct business questions an executive would 
want to ask SPECIFICALLY about this data. Reference real table/column names where helpful.
Focus on revenue trends, top performers, category breakdowns, and anomalies.
CRITICAL: Keep EACH question very short and punchy (under 10 words).
Return ONLY a valid JSON array of 4 strings. No markdown formatting or extra text.

AVAILABLE TABLES:
{db_index}

CORE SCHEMA (sample columns):
{schema}
"""

    try:
        response = llm.invoke(prompt)
        text = response.content.replace("```json", "").replace("```", "").strip()
        suggestions = json.loads(text)
        
        # Basic validation
        if isinstance(suggestions, list) and len(suggestions) >= 1:
            suggestions = suggestions[:4]
            if not context:
                _cached_general_suggestions = suggestions
            return {"suggestions": suggestions}
    except Exception as e:
        print("Suggestion generation failed:", e)
        pass

    # Fallback — generic but still useful
    fallback = [
        "What are the top 5 products by revenue?",
        "Show total orders by category as a bar chart",
        "Which customers have the highest lifetime value?",
        "Plot monthly sales trend as a line chart"
    ]
    return {"suggestions": fallback}

# ═══════════════════════════════════════════════
# 3. POLICY HUB
# ═══════════════════════════════════════════════

@app.post("/api/policy/search")
def policy_search(req: PolicyRequest):
    from agent import llm
    rag_results = _retrieve(req.query, k=3)
    if "DATA UNAVAILABLE" in rag_results:
        return {"answer": "No relevant policy documents found.", "chunks": []}
    answer = llm.invoke(
        f"Answer this question: '{req.query}' strictly using only this data:\n{rag_results}"
    ).content
    chunks = [c.strip() for c in rag_results.split("---") if c.strip()]
    return {"answer": answer, "chunks": chunks}

@app.post("/api/policy/upload")
async def upload_policy(file: UploadFile = File(...)):
    doc_path = config.DOCS_DIR / file.filename
    content = await file.read()
    with open(doc_path, "wb") as f:
        f.write(content)
    return {"success": True, "filename": file.filename}

@app.post("/api/policy/rebuild-vectordb")
def rebuild_vector_db():
    try:
        _build_and_get_vector_store()
        return {"success": True}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# ═══════════════════════════════════════════════
# 4. INTERACTIVE DASHBOARD
# ═══════════════════════════════════════════════

@app.get("/api/dashboard/chart")
def generate_dashboard_chart(
    table: str, x_col: str, y_col: str,
    chart_type: str = "bar", aggregation: str = "None", limit: int = 100
):
    from tools.visualizer_tool import _create_chart
    engine = get_engine()
    if aggregation != "None":
        query = f"SELECT {x_col}, {aggregation}({y_col}) AS {y_col} FROM {table} GROUP BY {x_col} ORDER BY {y_col} DESC LIMIT {limit}"
    else:
        query = f"SELECT {x_col}, {y_col} FROM {table} LIMIT {limit}"
    from sqlalchemy import text
    df = pd.read_sql(text(query), engine)
    if df.empty:
        raise HTTPException(status_code=404, detail="Query returned no data.")
    title = f"{aggregation} of {y_col} by {x_col}" if aggregation != "None" else f"{y_col} by {x_col}"
    fig = _create_chart(df, chart_type, x_col, y_col, title)
    return {"plotly_json": fig.to_json(), "rows": df.to_dict(orient="records")}

@app.post("/api/dashboard/ai-insight")
def dashboard_ai_insight(payload: dict):
    from agent import llm
    df = pd.DataFrame(payload.get("rows", []))
    result = llm.invoke(
        f"You are a Senior Data Analyst. Write a 3 sentence hard-hitting business insight about this data:\n{df.to_string(index=False)}"
    )
    return {"insight": result.content}

# ═══════════════════════════════════════════════
# 5. REPORT GENERATION
# ═══════════════════════════════════════════════

@app.post("/api/report/generate")
def generate_report():
    import re, base64, urllib.parse

    report_prompt = (
        "You are an elite Business Intelligence Analyst generating an Executive Sales Report in pure HTML. "
        "Follow these steps EXACTLY in order:\n\n"
        "STEP 1 - Run these SQL queries one by one using sql_query_tool:\n"
        "  a) SELECT Category, SUM(Sales_Amount) as Total_Sales FROM sales GROUP BY Category ORDER BY Total_Sales DESC LIMIT 10\n"
        "  b) SELECT Region, SUM(Sales_Amount) as Total_Sales FROM sales GROUP BY Region ORDER BY Total_Sales DESC\n"
        "  c) SELECT strftime('%Y-%m', Order_Date) as Month, SUM(Sales_Amount) as Monthly_Sales FROM sales GROUP BY Month ORDER BY Month\n"
        "  d) SELECT Discount, AVG(Profit) as Avg_Profit FROM sales GROUP BY Discount ORDER BY Discount\n"
        "  e) SELECT Sub_Category, COUNT(*) as Order_Count, SUM(Sales_Amount) as Total FROM sales GROUP BY Sub_Category ORDER BY Total DESC LIMIT 15\n"
        "  (Adjust column/table names if they differ in the actual schema)\n\n"
        "STEP 2 - For EACH query result, immediately call visualization_tool to create a chart:\n"
        "  a) bar chart: Category vs Total_Sales\n"
        "  b) pie chart: Region vs Total_Sales\n"
        "  c) line chart: Month vs Monthly_Sales\n"
        "  d) scatter chart: Discount vs Avg_Profit\n"
        "  e) bar chart: Sub_Category vs Total\n\n"
        "STEP 3 - Output a complete HTML document with:\n"
        "  - A styled header with company name and report date\n"
        "  - KPI summary cards at the top (Total Revenue, Total Orders, Avg Order Value, Top Region)\n"
        "  - Each chart embedded using: <iframe src='FILE_PATH_FROM_TOOL' width='100%' height='500px' style='border:none;'></iframe>\n"
        "  - 2-3 sentences of business insight below each chart\n"
        "  - Clean CSS: white background, Inter font, card shadows, professional layout\n\n"
        "CRITICAL RULES:\n"
        "- NEVER query raw rows — always use GROUP BY + aggregate functions (SUM, COUNT, AVG)\n"
        "- Always call visualization_tool after each SQL query before moving to the next\n"
        "- Use the EXACT file path returned by visualization_tool in the iframe src\n"
        "- Return ONLY the raw HTML document, no markdown, no code blocks\n"
    )
    report_content = run_agent(report_prompt)
    if "```html" in report_content:
        report_content = report_content.split("```html")[1].split("```")[0].strip()
    elif "```" in report_content:
        report_content = report_content.replace("```", "").strip()

    def embed_file(path_raw: str) -> str | None:
        """Try to read a local file and return a data URI, or None if not found."""
        # Decode URL encoding and normalize slashes
        path = urllib.parse.unquote(path_raw)
        path = path.replace("%3A", ":").replace("/", os.sep).replace("\\", os.sep)
        # Strip leading slash that appears in file:///C:/... → /C:/...
        if path.startswith(os.sep) and len(path) > 2 and path[1].isalpha() and path[2] == ":":
            path = path[1:]
        if not os.path.exists(path):
            # Try outputs dir as fallback
            basename = os.path.basename(path)
            fallback = config.OUTPUTS_DIR / basename
            if fallback.exists():
                path = str(fallback)
            else:
                return None
        ext = os.path.splitext(path)[1].lower()
        try:
            if ext in (".html", ".htm"):
                with open(path, "r", encoding="utf-8", errors="ignore") as f:
                    content = f.read()
                return f"data:text/html;charset=utf-8,{urllib.parse.quote(content)}"
            elif ext == ".png":
                with open(path, "rb") as f:
                    content = f.read()
                b64 = base64.b64encode(content).decode("utf-8")
                return f"data:image/png;base64,{b64}"
            elif ext in (".jpg", ".jpeg"):
                with open(path, "rb") as f:
                    content = f.read()
                b64 = base64.b64encode(content).decode("utf-8")
                return f"data:image/jpeg;base64,{b64}"
            elif ext == ".svg":
                with open(path, "r", encoding="utf-8", errors="ignore") as f:
                    content = f.read()
                b64 = base64.b64encode(content.encode("utf-8")).decode("utf-8")
                return f"data:image/svg+xml;base64,{b64}"
        except Exception:
            return None
        return None

    def make_portable(html_txt: str) -> str:
        # 1. Replace <iframe src="file:///..."> and <iframe src="C:\...">
        def replace_iframe(m):
            data_uri = embed_file(m.group(1))
            if data_uri:
                return f'src="{data_uri}"'
            return m.group(0)

        # file:/// URIs in src attributes
        html_txt = re.sub(r'src=["\']file:///([^"\']+)["\']', replace_iframe, html_txt)

        # Windows absolute paths in src (C:\... or C:/...)
        html_txt = re.sub(r'src=["\']([A-Za-z]:[/\\][^"\']+)["\']', replace_iframe, html_txt)

        # 2. Replace <img src="..."> with same patterns
        def replace_img(m):
            data_uri = embed_file(m.group(1))
            if data_uri:
                return f'src="{data_uri}"'
            return m.group(0)

        html_txt = re.sub(r'src=["\']file:///([^"\']+\.(png|jpg|jpeg|svg))["\']', replace_img, html_txt, flags=re.IGNORECASE)
        html_txt = re.sub(r'src=["\']([A-Za-z]:[/\\][^"\']+\.(png|jpg|jpeg|svg))["\']', replace_img, html_txt, flags=re.IGNORECASE)

        # 3. Minify whitespace between tags
        html_txt = re.sub(r'>\s{2,}<', '><', html_txt)
        return html_txt

    return {"html": make_portable(report_content)}

@app.post("/api/report/email")
def email_report(req: EmailReportRequest):
    try:
        msg = EmailMessage()
        msg["Subject"] = "📊 AI Executive Sales Report"
        msg["From"] = config.SENDER_EMAIL
        msg["To"] = req.recipient_email
        msg.set_content("Please find the attached AI-generated Sales Report.")
        msg.add_attachment(req.html_content.encode("utf-8"), maintype="text", subtype="html",
                           filename="Executive_Sales_Report.html")
        server = smtplib.SMTP(config.SMTP_SERVER, config.SMTP_PORT)
        server.ehlo(); server.starttls()
        server.login(config.SENDER_EMAIL, config.SENDER_PASSWORD)
        server.send_message(msg); server.quit()
        return {"success": True}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# ═══════════════════════════════════════════════
# 6. SCHEDULER
# ═══════════════════════════════════════════════

import sys as _sys
TASK_NAME = "AI_Executive_Sales_Report"
SCRIPT_PATH = str(config.BASE_DIR / "scripts" / "cron_report_sender.py")
# Always use the same Python interpreter that is running uvicorn right now
PYTHON_PATH = _sys.executable

@app.get("/api/scheduler/status")
def get_scheduler_status():
    try:
        result = subprocess.run(
            ["schtasks", "/query", "/tn", TASK_NAME, "/fo", "LIST"],
            capture_output=True, text=True, timeout=5
        )
        if result.returncode == 0:
            for line in result.stdout.splitlines():
                if "Next Run Time" in line:
                    return {"status": "active", "next_run": line.split(":", 1)[1].strip()}
            return {"status": "active", "next_run": "Unknown"}
        return {"status": "inactive"}
    except Exception:
        return {"status": "unknown"}

@app.post("/api/scheduler/update")
def update_scheduler(req: ScheduleRequest):
    try:
        if not req.enabled:
            # Just delete the task
            result = subprocess.run(
                f'schtasks /delete /tn "{TASK_NAME}" /f',
                capture_output=True, text=True, timeout=10, shell=True
            )
        else:
            if not req.recipient_email:
                raise HTTPException(status_code=400, detail="Recipient email is required.")
            # Build the full command as a single quoted string for shell=True
            # schtasks requires: /TR "\"path\" \"script\" arg"
            tr_inner = f'\\"{PYTHON_PATH}\\" \\"{SCRIPT_PATH}\\" {req.recipient_email}'
            shell_cmd = f'schtasks /create /tn "{TASK_NAME}" /tr "{tr_inner}" /sc DAILY /st {req.time_str} /f'
            result = subprocess.run(
                shell_cmd,
                capture_output=True, text=True, timeout=10, shell=True
            )
        if result.returncode == 0:
            return {"success": True, "message": "Scheduler updated successfully."}
        raise HTTPException(status_code=500, detail=(result.stderr or result.stdout).strip())
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/scheduler/send-now")
def send_report_now(recipient_email: str = Form(...)):
    try:
        spec = importlib.util.spec_from_file_location(
            "cron_report_sender",
            str(config.BASE_DIR / "scripts" / "cron_report_sender.py")
        )
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        html_content = mod.generate_report()
        msg = EmailMessage()
        msg["Subject"] = "📊 AI Executive Sales Report"
        msg["From"] = config.SENDER_EMAIL
        msg["To"] = recipient_email
        msg.set_content("Please find the attached AI-generated Sales Report.")
        msg.add_attachment(html_content.encode("utf-8"), maintype="text", subtype="html",
                           filename="Executive_Sales_Report.html")
        server = smtplib.SMTP(config.SMTP_SERVER, config.SMTP_PORT)
        server.ehlo(); server.starttls()
        server.login(config.SENDER_EMAIL, config.SENDER_PASSWORD)
        server.send_message(msg); server.quit()
        return {"success": True}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# ═══════════════════════════════════════════════
# 7. STAR SCHEMA
# ═══════════════════════════════════════════════

@app.get("/api/schema/tables", response_model=list[TableMetaOut])
def get_schema_tables():
    try:
        engine = get_engine()
        from sqlalchemy import text
        with engine.connect() as conn:
            res = conn.execute(text("SELECT table_name, description, updated_at FROM table_embeddings ORDER BY table_name"))
            rows = res.fetchall()
        
        out = []
        for r in rows:
            updated_at_str = r[2].isoformat() if r[2] else None
            out.append(TableMetaOut(table_name=r[0], description=r[1], updated_at=updated_at_str))
        return out
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/schema/sync")
def trigger_schema_sync():
    try:
        from scripts.sync_schema import sync_schema
        from scripts.embed_schema import sync_embeddings
        sync_schema()
        counts = sync_embeddings()
        return {
            "success": True,
            "tables_added": counts.get("embedded", 0),
            "tables_updated": counts.get("embedded", 0),
            "tables_skipped": counts.get("skipped", 0)
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

METADATA_PATH = config.DATA_DIR / "schema_metadata.json"

@app.get("/api/schema/relationships")
def get_relationships():
    if METADATA_PATH.exists():
        with open(METADATA_PATH) as f:
            return json.load(f)
    return {"relationships": []}

@app.post("/api/schema/relationships/auto-map")
def auto_map_relationships():
    from tools.sql_tool import get_schema, get_engine
    from agent import llm
    import sqlalchemy

    # ── Bust ALL caches so newly-added/removed tables are always picked up fresh ──
    import tools.sql_tool as sql_mod
    sql_mod._schema_cache = None
    sql_mod._db_index_cache = None

    # Wipe the saved relationships — we'll rebuild from scratch with the current schema
    if METADATA_PATH.exists():
        with open(METADATA_PATH, "w") as f:
            json.dump({"relationships": []}, f)

    schema = get_schema()

    # Derive the active DB filename dynamically
    engine = get_engine()
    try:
        db_filename = os.path.basename(str(engine.url.database))
    except Exception:
        db_filename = "database.db"

    prompt = f"""
You are an expert Database Architect. Analyze the following database schema and identify ALL logical
Foreign Key → Primary Key relationships between tables.

Return ONLY a valid JSON array of relationship objects — no markdown, no extra text.
Each object MUST have EXACTLY these keys:
  "source_db"     (string: the active database filename, e.g. "{db_filename}")
  "source_table"  (string: the table that holds the foreign key)
  "source_column" (string: the foreign key column name)
  "target_db"     (string: the active database filename, e.g. "{db_filename}")
  "target_table"  (string: the referenced table)
  "target_column" (string: the referenced primary key column)
  "type"          (string: exactly one of "Many-to-One", "One-to-One", or "One-to-Many")

Rules:
- Include ALL tables shown in the schema, not just the core sales tables.
- If a column name ends in _id and a matching table exists, treat it as a FK.
- Use the PRAGMA FK information when present.
- Do NOT invent relationships that are not supported by the schema.

ACTIVE DB: {db_filename}

SCHEMA:
{schema}
"""
    try:
        res = llm.invoke(prompt)
        text = res.content.replace("```json", "").replace("```", "").strip()
        new_rels = json.loads(text)
        if not isinstance(new_rels, list):
            return {"success": False, "error": "LLM did not return a list"}

        # ── Merge: load existing, append new ones that aren’t already present ──
        existing = []
        if METADATA_PATH.exists():
            with open(METADATA_PATH) as f:
                existing = json.load(f).get("relationships", [])

        def rel_key(r):
            return (r.get("source_table"), r.get("source_column"),
                    r.get("target_table"), r.get("target_column"))

        existing_keys = {rel_key(r) for r in existing}
        added = []
        for r in new_rels:
            if rel_key(r) not in existing_keys:
                existing.append(r)
                existing_keys.add(rel_key(r))
                added.append(r)

        meta = {"relationships": existing}
        with open(METADATA_PATH, "w") as f:
            json.dump(meta, f, indent=4)

        return {"success": True, "relationships": existing, "added": len(added)}
    except Exception as e:
        print("Auto-map failed:", e)
        return {"success": False, "error": str(e)}

@app.post("/api/schema/relationships")
def add_relationship(rel: SchemaRelationship):
    meta = {"relationships": []}
    if METADATA_PATH.exists():
        with open(METADATA_PATH) as f:
            meta = json.load(f)
    meta["relationships"].append(rel.dict())
    with open(METADATA_PATH, "w") as f:
        json.dump(meta, f, indent=4)
    return {"success": True}

@app.delete("/api/schema/relationships")
def clear_relationships():
    if METADATA_PATH.exists():
        os.remove(METADATA_PATH)
    return {"success": True}

# ═══════════════════════════════════════════════
# 8. HEALTH
# ═══════════════════════════════════════════════

@app.get("/api/health")
def health():
    return {"status": "ok", "model": config.MODEL_NAME}

@app.delete("/api/schema/relationships/{index}")
def delete_relationship(index: int):
    if not METADATA_PATH.exists():
        raise HTTPException(status_code=404, detail="No relationships found")
    with open(METADATA_PATH) as f:
        meta = json.load(f)
    rels = meta.get("relationships", [])
    if index < 0 or index >= len(rels):
        raise HTTPException(status_code=404, detail="Index out of range")
    rels.pop(index)
    meta["relationships"] = rels
    with open(METADATA_PATH, "w") as f:
        json.dump(meta, f, indent=4)
    return {"success": True}