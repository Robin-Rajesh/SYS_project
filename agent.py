"""
agent.py — LangChain ReAct Agent Powered by Google Gemini
==========================================================
Uses langgraph's create_react_agent to build a tool-calling agent with:
- Gemini LLM (temperature=0)
- Three tools: sql_query_tool, policy_search_tool, visualization_tool
- A detailed system prompt preventing hallucination
- Financial-year-aware quarter resolution (Q4 = Jan–Mar, the year-end quarter)
- Conversation memory (last 10 exchanges kept in a message list)
- A single entry point: run_agent(user_input) → str
"""

from langchain_google_genai import ChatGoogleGenerativeAI
from langgraph.prebuilt import create_react_agent
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage
import json
from datetime import date

import config
from tools.sql_tool import sql_query_tool, inspect_table_columns
from tools.rag_tool import policy_search_tool
from tools.visualizer_tool import visualization_tool


# ═══════════════════════════════════════════════════════════════
# 1. FINANCIAL QUARTER RESOLVER
# ═══════════════════════════════════════════════════════════════

def _resolve_financial_quarters() -> str:
    """
    Returns a string block describing the financial year quarter mapping
    and pre-computes 'last quarter', 'this quarter', etc. relative to today.

    Financial Year definition (April → March):
        Q1 = April   – June      (months 4–6)
        Q2 = July    – September (months 7–9)
        Q3 = October – December  (months 10–12)
        Q4 = January – March     (months 1–3)  ← year-end / "last quarter"

    'Last quarter' always refers to Q4 (January–March) of the most recent
    completed financial year because that is the financial year-end quarter.
    """
    today = date.today()
    current_month = today.month
    current_year  = today.year

    # Determine which FY quarter we are currently in
    if 4 <= current_month <= 6:
        current_fy_q = "Q1"
        current_q_months = "April–June"
        current_q_year   = current_year
        last_q_label     = "Q4 (January–March)"
        last_q_start     = f"{current_year - 1}-01-01"
        last_q_end       = f"{current_year - 1}-03-31"
    elif 7 <= current_month <= 9:
        current_fy_q = "Q2"
        current_q_months = "July–September"
        current_q_year   = current_year
        last_q_label     = "Q1 (April–June)"
        last_q_start     = f"{current_year}-04-01"
        last_q_end       = f"{current_year}-06-30"
    elif 10 <= current_month <= 12:
        current_fy_q = "Q3"
        current_q_months = "October–December"
        current_q_year   = current_year
        last_q_label     = "Q2 (July–September)"
        last_q_start     = f"{current_year}-07-01"
        last_q_end       = f"{current_year}-09-30"
    else:  # January–March
        current_fy_q = "Q4"
        current_q_months = "January–March"
        current_q_year   = current_year
        last_q_label     = "Q3 (October–December)"
        last_q_start     = f"{current_year - 1}-10-01"
        last_q_end       = f"{current_year - 1}-12-31"

    is_pg = config.IS_CLOUD
    date_fn = "EXTRACT(MONTH FROM date_column)" if is_pg else "strftime('%m', date_column)"
    
    return f"""
FINANCIAL YEAR & QUARTER DEFINITIONS (CRITICAL — READ CAREFULLY):
==================================================================
This business uses an April–March financial year. Quarter mapping:

  Q1  =  April     – June       (months 4, 5, 6)
  Q2  =  July      – September  (months 7, 8, 9)
  Q3  =  October   – December   (months 10, 11, 12)
  Q4  =  January   – March      (months 1, 2, 3)   ← YEAR-END QUARTER

TODAY: {today.isoformat()}
CURRENT FINANCIAL QUARTER: {current_fy_q} ({current_q_months} {current_q_year})

TERM RESOLUTION RULES — apply these BEFORE writing any SQL:
  • "last quarter"    → Q4 = January to March, i.e. {last_q_start} to {last_q_end}
                        (Q4 is ALWAYS the "last quarter" because it is the
                         financial year-end quarter, regardless of calendar date)
  • "this quarter"    → {current_fy_q} ({current_q_months} {current_q_year})
  • "Q1" alone        → April–June   → (Months 4, 5, 6)
  • "Q2" alone        → July–Sep     → (Months 7, 8, 9)
  • "Q3" alone        → Oct–Dec      → (Months 10, 11, 12)
  • "Q4" alone        → Jan–Mar      → (Months 1, 2, 3)

SYNTAX NOTE (Using {'PostgreSQL' if is_pg else 'SQLite'}):
  • Use {date_fn} for month extraction.
"""


# ═══════════════════════════════════════════════════════════════
# 2. NORMALIZED SCHEMA DESCRIPTION
# ═══════════════════════════════════════════════════════════════

NORMALIZED_SCHEMA = """
DATABASE: sales_normalized.db  (SQLite, 100 000 orders, 2020-01-01 → 2024-12-31)
=========================================================================
The database is fully normalised into 6 tables. ALWAYS JOIN — never assume
denormalised columns exist on orders directly.

TABLE: orders
  order_id       TEXT   – primary key  (e.g. 'ORD-0000001')
  customer_id    TEXT   – FK → customers.customer_id
  location_id    INTEGER – FK → locations.location_id
  product_id     TEXT   – FK → products.product_id
  ship_mode_id   INTEGER – FK → shipping_methods.ship_mode_id
  rep_id         INTEGER – FK → sales_reps.rep_id
  order_date     TEXT   – 'YYYY-MM-DD' (use strftime() for date math)
  ship_date      TEXT   – 'YYYY-MM-DD'
  quantity       INTEGER
  sales_amount   REAL
  discount       REAL
  discount_tier  TEXT
  profit         REAL
  profit_margin  REAL
  payment_mode   TEXT
  return_status  TEXT

TABLE: customers
  customer_id      TEXT  – PK
  customer_name    TEXT
  customer_segment TEXT  (e.g. 'Consumer', 'Corporate', 'Home Office')

TABLE: products
  product_id    TEXT – PK
  product_name  TEXT
  category      TEXT  (e.g. 'Furniture', 'Office Supplies', 'Technology')
  sub_category  TEXT
  cost_price    REAL
  selling_price REAL

TABLE: locations
  location_id  INTEGER – PK
  city         TEXT
  state        TEXT
  region       TEXT  (e.g. 'East', 'West', 'North', 'South')

TABLE: shipping_methods
  ship_mode_id  INTEGER – PK
  ship_mode     TEXT  (e.g. 'First Class', 'Same Day', 'Second Class', 'Standard Class')

TABLE: sales_reps
  rep_id    INTEGER – PK
  sales_rep TEXT

STANDARD JOIN TEMPLATE (copy-paste and extend as needed):
  SELECT ...
  FROM   orders o
  JOIN   customers        c  ON o.customer_id  = c.customer_id
  JOIN   products         p  ON o.product_id   = p.product_id
  JOIN   locations        l  ON o.location_id  = l.location_id
  JOIN   shipping_methods sm ON o.ship_mode_id = sm.ship_mode_id
  JOIN   sales_reps       sr ON o.rep_id       = sr.rep_id
  WHERE  ...
"""


# ═══════════════════════════════════════════════════════════════
# 3. DYNAMIC SYSTEM PROMPT
# ═══════════════════════════════════════════════════════════════

def get_system_prompt() -> str:
    """
    Generates the system prompt dynamically.
    Injects:
      - The normalised schema description
      - Real-time financial quarter resolution
      - Cross-database relationship metadata (if present)
    """
    from tools.sql_tool import get_schema, get_db_index

    live_schema = get_schema()          # schema of whichever DB is currently connected
    db_index = get_db_index()           # Index of ALL tables
    quarter_block = _resolve_financial_quarters()

    # Load Star Schema relationships if defined
    metadata_path = config.DATA_DIR / "schema_metadata.json"
    relationships_str = "No cross-database relationships defined yet."
    if metadata_path.exists():
        try:
            with open(metadata_path, "r") as f:
                metadata = json.load(f)
            if metadata.get("relationships"):
                rel_lines = []
                for rel in metadata["relationships"]:
                    rel_lines.append(
                        f"- {rel['source_table']} ({rel['source_db']}).{rel['source_column']}"
                        f" -> {rel['target_table']} ({rel['target_db']}).{rel['target_column']}"
                        f" [{rel['type']}]"
                    )
                relationships_str = "\n".join(rel_lines)
        except Exception:
            pass

    return f"""\
You are an expert Data Analyst AI assistant with access to these tools:

1. sql_query_tool        – Query the connected SQL database (SELECT only).
2. inspect_table_columns – Get column details for a specific table. 
3. policy_search_tool    – Search internal policy documents.
4. visualization_tool   – Generate charts.

{quarter_block}

{NORMALIZED_SCHEMA}

--- SCALABLE SCHEMA DISCOVERY ---
You have a 'Core Schema' below (the most important tables), but the database might have 100s more. 
If a question refers to a table in the 'TABLE NAME INDEX' that you don't have columns for, 
you MUST call 'inspect_table_columns' to see its schema before writing your SQL.

CORE SCHEMA (Primary Tables):
{live_schema}

DATABASE INDEX (Full list of all tables):
{db_index}

ENTERPRISE STAR SCHEMA RELATIONSHIPS:
{relationships_str}

MULTI-DATABASE CAPABILITY:
  All .db files in /data are automatically ATTACHED. Use the filename
  (without .db) as the schema prefix for cross-database joins.
  Example: SELECT * FROM sales_normalized JOIN users.users ON ...

STRICT RULES:
  - NEVER invent data or column names. 
  - If you need a table from the INDEX but don't know its columns, call 'inspect_table_columns'.
  - If data is unavailable: respond "DATA UNAVAILABLE: [reason]"
  - For charts: call sql_query_tool first, then visualization_tool.
  - RULE: NEVER print file paths like 'C:\...\outputs\chart.html' in your final response. The UI renders the charts automatically.
  - Format your final answer clearly with sections if needed.
  - RULE MANDATORY: You MUST end every single analytical response with the exact SQL query you executed. Wrap it EXACTLY in a markdown block like this:
```sql
SELECT ...
```
"""


# ═══════════════════════════════════════════════════════════════
# 4. LLM INITIALIZATION
# ═══════════════════════════════════════════════════════════════

llm = ChatGoogleGenerativeAI(
    model=config.MODEL_NAME,
    google_api_key=config.GOOGLE_API_KEY,
    temperature=0,
    timeout=600.0,
    max_retries=5,
)

# ═══════════════════════════════════════════════════════════════
# 5. TOOL LIST & REACT AGENT
# ═══════════════════════════════════════════════════════════════

tools = [sql_query_tool, inspect_table_columns, policy_search_tool, visualization_tool]


def _state_modifier(state):
    """Prepends the freshest system prompt into the message state."""
    return [SystemMessage(content=get_system_prompt())] + state["messages"]


agent = create_react_agent(
    model=llm,
    tools=tools,
    prompt=_state_modifier,
)

# ═══════════════════════════════════════════════════════════════
# 6. CONVERSATION MEMORY
# ═══════════════════════════════════════════════════════════════

_chat_history: list = []
_MEMORY_WINDOW = 10  # keep last 10 user/assistant pairs


def _trim_history():
    """Keep only the last _MEMORY_WINDOW pairs of messages."""
    global _chat_history
    max_messages = _MEMORY_WINDOW * 2
    if len(_chat_history) > max_messages:
        _chat_history = _chat_history[-max_messages:]


# ═══════════════════════════════════════════════════════════════
# 7. PUBLIC ENTRY POINTS
# ═══════════════════════════════════════════════════════════════

def _extract_text(content) -> str:
    """Safely extracts text from the LLM's content field."""
    if isinstance(content, list):
        texts = []
        for item in content:
            if isinstance(item, dict) and "text" in item:
                texts.append(item["text"])
            elif isinstance(item, str):
                texts.append(item)
        return " ".join(texts)
    return str(content)


def run_agent(user_input: str) -> str:
    """
    Send a user message to the agent and return its text response.
    """
    global _chat_history
    try:
        _chat_history.append(HumanMessage(content=user_input))
        _trim_history()

        result = agent.invoke({"messages": _chat_history})

        response_messages = result.get("messages", [])
        ai_response = ""

        for msg in reversed(response_messages):
            if hasattr(msg, "content") and msg.content:
                text = _extract_text(msg.content).strip()
                if text and text != "None":
                    ai_response = text
                    break

        if not ai_response:
            all_content = [
                _extract_text(m.content)
                for m in response_messages
                if hasattr(m, "content") and m.content
            ]
            if all_content:
                ai_response = max(all_content, key=len)
            else:
                with open("outputs/debug_agent.txt", "w", encoding="utf-8") as f:
                    f.write(f"Result dump:\n{result}\n\n")
                ai_response = "No response generated."

        _chat_history.append(AIMessage(content=ai_response))
        _trim_history()
        return ai_response

    except Exception as e:
        return (
            f"AGENT ERROR: Unable to process this request. "
            f"Please rephrase.\n(Debug: {e})"
        )


def stream_agent(user_input: str):
    """
    Yields intermediate steps from the agent for streaming UIs.
    """
    global _chat_history
    try:
        _chat_history.append(HumanMessage(content=user_input))
        _trim_history()

        final_response = ""
        for step in agent.stream({"messages": _chat_history}):
            yield step
            if "agent" in step:
                msg = step["agent"]["messages"][-1]
                if getattr(msg, "content", ""):
                    final_response = _extract_text(msg.content)

        if not final_response:
            final_response = "No response generated."

        _chat_history.append(AIMessage(content=final_response))
        _trim_history()

    except Exception as e:
        yield {"error": str(e)}


def clear_memory():
    """Reset conversation memory."""
    global _chat_history
    _chat_history.clear()