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

import config
from agent import stream_agent, run_agent, clear_memory
from tools.sql_tool import set_database_connection, get_engine
from tools.rag_tool import _retrieve, _build_vector_store

# ─────────────────────────────────────────────
app = FastAPI(title="Enterprise Data Analyst AI", version="1.0.0")

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

# ═══════════════════════════════════════════════
# 1. DATABASE
# ═══════════════════════════════════════════════

@app.get("/api/databases")
def list_databases():
    files = [f for f in os.listdir(config.DATA_DIR) if f.endswith((".db", ".sqlite"))]
    return {"databases": files, "active": str(config.DB_PATH)}

@app.post("/api/databases/connect")
def connect_database(req: DbConnectRequest):
    uri = f"sqlite:///{config.DATA_DIR / req.db_filename}"
    try:
        set_database_connection(uri)
        clear_memory()
        return {"success": True, "uri": uri}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.get("/api/tables")
def list_tables(db_filename: Optional[str] = None):
    if db_filename:
        engine = create_engine(f"sqlite:///{config.DATA_DIR / db_filename}")
    else:
        engine = get_engine()
    tables = inspect(engine).get_table_names()
    return {"tables": tables}

@app.get("/api/tables/{table_name}/columns")
def get_columns(table_name: str, db_filename: Optional[str] = None):
    if db_filename:
        engine = create_engine(f"sqlite:///{config.DATA_DIR / db_filename}")
    else:
        engine = get_engine()
    cols = [{"name": c["name"], "type": str(c["type"])}
            for c in inspect(engine).get_columns(table_name)]
    return {"columns": cols}

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
    # Build WHERE clause
    if global_search:
        # Search across all text columns
        cols = [c["name"] for c in inspect(engine).get_columns(table_name)]
        like_clauses = " OR ".join([f"CAST({col} AS TEXT) LIKE '%{global_search}%'" for col in cols])
        where = f"WHERE ({like_clauses})"
    elif filter_col and filter_val:
        where = f"WHERE {filter_col} LIKE '%{filter_val}%'"
    else:
        where = ""
    order = f"ORDER BY {sort_col} {sort_order}" if sort_col else ""
    offset = (page - 1) * page_size
    try:
        count_df = pd.read_sql(f"SELECT COUNT(*) as c FROM {table_name} {where}", engine)
        total = int(count_df.iloc[0, 0])
    except Exception:
        total = 0
    df = pd.read_sql(
        f"SELECT * FROM {table_name} {where} {order} LIMIT {page_size} OFFSET {offset}", engine
    )
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
    df = pd.read_sql(f"SELECT * FROM {table_name} LIMIT 10", engine)
    prompt = (
        f"You are an AI Data Quality Engineer. Review this table schema {schema_info} "
        f"and the following data snippet:\n{df.head(10).to_string(index=False)}\n"
        f"Identify 2 potential data quality risks or anomalies. Keep it concise."
    )
    result = llm.invoke(prompt)
    return {"insight": result.content}

# ═══════════════════════════════════════════════
# 2. AGENT CHAT (SSE streaming)
# ═══════════════════════════════════════════════

@app.post("/api/chat/stream")
async def chat_stream(req: ChatRequest):
    async def generate() -> AsyncGenerator[str, None]:
        final_response = "No response generated."
        plotly_json = None

        for step in stream_agent(req.message):
            if "agent" in step:
                msgs = step["agent"].get("messages", [])
                if msgs:
                    msg = msgs[-1]
                    if getattr(msg, "tool_calls", None):
                        for tc in msg.tool_calls:
                            event = {"type": "tool_call", "name": tc["name"], "args": str(tc["args"])}
                            yield f"data: {json.dumps(event)}\n\n"
                            if tc["name"] == "visualization_tool":
                                try:
                                    from tools.visualizer_tool import _create_chart
                                    payload = json.loads(tc["args"].get("input_json", "{}"))
                                    df = pd.DataFrame(payload.get("data", []))
                                    if not df.empty:
                                        fig = _create_chart(
                                            df,
                                            payload.get("chart_type", "bar"),
                                            payload.get("x_column", ""),
                                            payload.get("y_column", ""),
                                            payload.get("title", ""),
                                            payload.get("color_column", "")
                                        )
                                        plotly_json = fig.to_json()
                                except Exception:
                                    pass
                    content = ""
                    if hasattr(msg, "content"):
                        if isinstance(msg.content, str):
                            content = msg.content
                        elif isinstance(msg.content, list):
                            content = " ".join(
                                m.get("text", "") if isinstance(m, dict) else str(m)
                                for m in msg.content
                            )
                    if content.strip():
                        final_response = content

            elif "tools" in step:
                msgs = step["tools"].get("messages", [])
                if msgs:
                    yield f"data: {json.dumps({'type': 'tool_result', 'content': msgs[-1].content[:500]})}\n\n"

            elif "error" in step:
                yield f"data: {json.dumps({'type': 'error', 'content': step['error']})}\n\n"

        if final_response == "No response generated.":
            final_response = "I have successfully processed your request."

        response_event = {"type": "response", "content": final_response}
        if plotly_json:
            response_event["plotly_json"] = plotly_json
        yield f"data: {json.dumps(response_event)}\n\n"
        yield 'data: {"type": "done"}\n\n'

    return StreamingResponse(generate(), media_type="text/event-stream")

@app.post("/api/chat/clear")
def clear_chat():
    clear_memory()
    return {"success": True}

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
        _build_vector_store()
        return {"success": True}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# ═══════════════════════════════════════════════
# 3b. HYBRID SEARCH
# ═══════════════════════════════════════════════

class HybridSearchRequest(BaseModel):
    query: str

@app.post("/api/hybrid-search")
def hybrid_search(req: HybridSearchRequest):
    """
    Fires SQL (NL→SQL→execute) and RAG (ChromaDB similarity search)
    concurrently, then synthesizes results with Gemini.
    Returns structured JSON with both result lanes plus an AI insight.
    """
    try:
        from tools.hybrid_tool import run_hybrid_search
        result = run_hybrid_search(req.query)
        return result
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
    df = pd.read_sql(query, engine)
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
                b64 = base64.b64encode(content.encode("utf-8")).decode("utf-8")
                return f"data:text/html;base64,{b64}"
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

TASK_NAME = "AI_Executive_Sales_Report"
SCRIPT_PATH = str(config.BASE_DIR / "scripts" / "cron_report_sender.py")
PYTHON_PATH = str(config.BASE_DIR / "venv" / "Scripts" / "python.exe")

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
    # On Windows, schtasks /TR needs specific quoting to handle spaces and arguments together.
    # We use a single string with internal escaped quotes for the task run command.
    tr_command = f'\\"{PYTHON_PATH}\\" \\"{SCRIPT_PATH}\\" {req.recipient_email}'

    cmd = (
        ["schtasks", "/delete", "/tn", TASK_NAME, "/f"] if not req.enabled else
        ["schtasks", "/create", "/tn", TASK_NAME,
         "/tr", tr_command,
         "/sc", "DAILY", "/st", req.time_str, "/f"]
    )
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
        if result.returncode == 0:
            return {"success": True}
        raise HTTPException(status_code=500, detail=result.stderr or result.stdout)
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

METADATA_PATH = config.DATA_DIR / "schema_metadata.json"

@app.get("/api/schema/relationships")
def get_relationships():
    if METADATA_PATH.exists():
        with open(METADATA_PATH) as f:
            return json.load(f)
    return {"relationships": []}

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