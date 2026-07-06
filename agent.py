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

from langchain_google_genai import ChatGoogleGenerativeAI, HarmCategory, HarmBlockThreshold
from langgraph.prebuilt import create_react_agent
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage
import json
from datetime import date
from typing import Optional

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
# 2. SCHEMA DEFINITION IS NOW FULLY DYNAMIC
# ═══════════════════════════════════════════════════════════════
# The schema is now injected entirely via live_schema to support
# both local SQLite and Cloud PostgreSQL without hallucinations.


# ═══════════════════════════════════════════════════════════════
# 3. DYNAMIC SYSTEM PROMPT
# ═══════════════════════════════════════════════════════════════

# Module-level cache: loaded once from Supabase (or JSON fallback) on first call.
_relationships_cache = None

def get_system_prompt(user_query: Optional[str] = None) -> str:
    """
    Generates the system prompt dynamically.
    Injects:
      - The normalised schema description
      - Real-time financial quarter resolution
      - Cross-database relationship metadata (if present)
    """
    from tools.sql_tool import get_db_index
    from tools.schema_retriever import get_resolved_schema_context

    live_schema = get_resolved_schema_context(user_query) # schema of whichever DB is currently connected
    db_index = get_db_index()           # Index of ALL tables
    quarter_block = _resolve_financial_quarters()

    # Load Star Schema relationships
    global _relationships_cache
    relationships_str = "No cross-database relationships defined yet."

    if _relationships_cache is None and config.IS_CLOUD:
        try:
            from tools.sql_tool import get_engine
            from sqlalchemy import text
            import pandas as pd
            with get_engine().connect() as conn:
                df = pd.read_sql(text("SELECT * FROM schema_relationships"), conn)
                if not df.empty:
                    _relationships_cache = df.to_dict(orient="records")
        except Exception as e:
            print(f"[Agent] Failed to load relationships from Supabase: {e}")
            _relationships_cache = []

    # Fallback to local JSON if not cloud, or cloud load failed
    if not _relationships_cache and not config.IS_CLOUD:
        metadata_path = config.DATA_DIR / "schema_metadata.json"
        if metadata_path.exists():
            try:
                with open(metadata_path, "r") as f:
                    metadata = json.load(f)
                if metadata.get("relationships"):
                    # Normalize JSON keys → same shape as schema_relationships table
                    _relationships_cache = [
                        {
                            "from_table": r["source_table"],
                            "to_table":   r["target_table"],
                            "from_col":   r["source_column"],
                            "to_col":     r["target_column"],
                        }
                        for r in metadata["relationships"]
                    ]
            except Exception:
                pass

    if _relationships_cache:
        rel_lines = [
            f"- {rel['from_table']}.{rel['from_col']} -> {rel['to_table']}.{rel['to_col']}"
            for rel in _relationships_cache
        ]
        relationships_str = "\n".join(rel_lines)

    return f"""\
You are an expert Data Analyst AI assistant with access to these tools:

1. sql_query_tool        – Query the connected SQL database (SELECT only).
2. inspect_table_columns – Get column details for a specific table. 
3. policy_search_tool    – Search internal policy documents.
4. visualization_tool   – Generate charts.

ZERO HALLUCINATION POLICY (CRITICAL OVERRIDE):
- MANDATORY TOOL USAGE: You MUST execute the sql_query_tool and wait for its results BEFORE generating any numbers or data in your final response. DO NOT just write a SQL query in your response without actually running it via the tool first.
- You are absolutely FORBIDDEN from hallucinating, guessing, or making up ANY information.
- Every single entity name, column name, table name, numeric value, and category MUST come directly from your tool outputs or the provided schema.
- If the data looks like dummy data (e.g., 'Cat_11', 'User_5'), you MUST output it exactly as is. Never translate, beautify, or invent realistic-sounding alternatives.
- If you do not know the answer, or if the database returns empty results, you must say "I do not have this data" instead of guessing.

DATABASE DIALECT: {'PostgreSQL' if config.IS_CLOUD else 'SQLite'} (Write EXACTLY this dialect. Never mix them!)

{quarter_block}

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
  - DETERMINISTIC SORTING (CRITICAL): You MUST ALWAYS include an `ORDER BY` clause on EVERY query that returns multiple rows. Without `ORDER BY`, SQL returns rows in random order, causing mismatched tables. Default to ordering by the primary key (e.g. `ORDER BY id ASC`).
  - NO PYTHON (CRITICAL): You are a SQL agent, NOT a Python data scientist. NEVER output `<execute_ipython>` tags, python code, or pandas scripts. You only write SQL and English text.
  - SCHEMA VERIFICATION (CRITICAL): You are FORBIDDEN from guessing column names. Before using ANY column in a SELECT, WHERE, or JOIN, you MUST verify it exists in the CORE SCHEMA. If the table is in the INDEX but not in the CORE SCHEMA, you MUST call 'inspect_table_columns' to fetch its exact columns BEFORE writing your query. Guessing column names will cause a fatal database error.
  - STRICT DATA FIDELITY (CRITICAL): You MUST output exactly the data values that the sql_query_tool returns. If the database returns generic names like 'Cat_11', you MUST output 'Cat_11'. DO NOT translate, map, or beautify these into real-world words like 'Toys' or 'Sports'. DO NOT make up fake numbers. Your text analysis MUST strictly match the numeric results from the tool.
  - NO PRODUCT NAME COLUMN: The products table does NOT have a product_name or name column. It only has product_id, category_id, supplier_id, and price. If you need a product name, you must join with the categories table and use category_name instead. DO NOT SELECT p.product_name.
  - COLUMN ALIAS RULES (CRITICAL): In the order_items table, the column for quantity is EXACTLY `qty`. DO NOT use `quantity`. Doing so will cause a fatal error.
  - RETURNS QUANTITY RULE (CRITICAL): A return row corresponds to an order_item, not a single item. To find the total quantity of items returned, you MUST join the returns table with order_items and use SUM(oi.qty). DO NOT use COUNT(return_id) to calculate returned item quantities.
  - ALWAYS use case-insensitive text matching specifically with `LOWER(column) LIKE LOWER('%value%')` to prevent empty results across different SQL dialects. NEVER use exact equality (=) with string literals for status/category/type columns.
  - ENUM / STATUS VALUE VERIFICATION (CRITICAL): When filtering on a categorical column whose values you do not know for certain (e.g. status, type, category, state, stage), you MUST first run a discovery query to see the actual distinct values in the database BEFORE writing the main query:
      SELECT DISTINCT status FROM shipments LIMIT 20;
    Use ONLY the values that actually appear in the result. NEVER assume values like 'RETURNED', 'ACTIVE', 'PENDING' — they may be spelled differently (e.g. 'returned', 'Return', 'RET'). If the result set is empty after filtering, it almost always means the filter value was wrong — re-verify.
  - If you need a table from the INDEX but don't know its columns, call 'inspect_table_columns' BEFORE writing the query.
  - Double check your SQL syntax carefully (e.g. GROUP BY columns).
  - SIMPSON'S PARADOX PREVENTION: When asked for average ratios (e.g. "average profit margin"), NEVER use `AVG(margin_column)`. You MUST mathematically calculate it as `SUM(numerator) / SUM(denominator)`.
  - WINDOW FUNCTION RULES: When calculating Month-over-Month (MoM) or Year-over-Year (YoY) growth, DO NOT hallucinate fake "growth" columns. You MUST calculate it using `LAG()` inside a CTE.
  - TIME RELATIVITY (CRITICAL): When queried about "last month", "last year", or "today", DO NOT use MySQL-specific functions like DATE_SUB. You MUST derive the reference date by running: `SELECT MAX(order_date) FROM orders` — this is the dataset's "today". The dataset's most recent date WILL be different from the real-world date shown above; do NOT be surprised if the SQL returns years like 2023 or 2024 instead of the current year. The sql_query_tool result is ALWAYS the ground truth — never override it with calendar-year assumptions.
  - UNKNOWN METRICS: If requested for a metric requiring columns that DO NOT exist (e.g. shipping costs), politely decline. DO NOT infer, guess, or use a flat integer.
  - TOP-N PER CATEGORY: When asked for the "Top 1 item per subcategory" (e.g. best rep per region), DO NOT mistakenly use a flat GROUP BY. You MUST use PostgreSQL window functions `ROW_NUMBER() OVER(PARTITION BY ... ORDER BY ... DESC)`.
  - ZERO-RESULT GUARD (CRITICAL — NO SUBSTITUTION): If sql_query_tool returns 0 rows OR a COUNT of 0, you MUST report exactly that — "The query returned 0 results." DO NOT substitute any number from prior conversation context. A result of 0 almost always means the filter value is wrong (e.g. wrong status string) — in that case, run the ENUM verification query (SELECT DISTINCT ...) and retry with the correct value before reporting a final answer.
  - If data is still unavailable after all retries: clearly say so, briefly explain the most likely reason (e.g. the filter value doesn't exist in the data, the column is absent, or the date range has no records), and then proactively suggest 2–3 specific alternative questions the user could ask that *would* return results from the available data.
  - For charts: call sql_query_tool first, then visualization_tool.
  - RULE: NEVER print file paths like 'C:\\...\\outputs\\chart.html' in your final response. The UI renders the charts automatically.
  - Format your final answer clearly with sections if needed.
  - FOLLOW-UP QUESTIONS: When a user asks a follow-up question (e.g. "Is their performance consistent over time?", "Show me a chart", "Break it down by region"), you MUST run the appropriate sql_query_tool call AND then write a complete, thorough text analysis of the results. NEVER silently finish after a tool call — always synthesize the data into an answer.
  - ALWAYS INCLUDE PRIMARY KEY IN ENTITY LISTINGS: When the question asks to list, rank, or compare entities (stores, customers, products, employees, etc.), you MUST always include the entity's primary key column (e.g. store_id, customer_id, product_id) in the SELECT and output — even if the user did not explicitly ask for it. Without the ID, rows from the same city/name/category are indistinguishable. Example: "rank all stores by revenue" → always SELECT store_id alongside city and revenue.

--- AMBIGUITY CLARIFICATION (CRITICAL — ASK BEFORE QUERYING) ---
  Before running ANY query, check whether the user's question is AMBIGUOUS on a key dimension.
  If it is ambiguous, DO NOT query — instead, ask a short, direct clarifying question.

  WHEN TO ASK:
  1. TIME AMBIGUITY — A month or quarter is mentioned but NO YEAR is specified.
     Examples that require clarification:
       • "Show March orders"         → Ask: "Which year would you like — or all years combined?"
       • "What were Q2 sales?"       → Ask: "Which financial year are you referring to?"
       • "Revenue last month"        → This is NOT ambiguous (use TIME RELATIVITY rule above).
  2. ENTITY AMBIGUITY — Multiple interpretations exist for an entity name (e.g. two products share a name).
  3. METRIC AMBIGUITY — The metric could mean different things (e.g. "performance" → sales? profit? orders?).

  HOW TO ASK:
  - Keep it concise: one sentence, one question.
  - Offer 2-3 quick options where possible.
  - Example response format:
      "Could you clarify which year you mean for March?
       Options: **2020**, **2021**, **2022**, **2023**, or **all years combined**."

  WHEN NOT TO ASK:
  - If the user says "all time", "overall", "total across all years", "combined" — proceed without asking.
  - If the question uses relative time ("last month", "this quarter", "last year") — use the TIME RELATIVITY rule.
  - If context from the conversation already makes the time period clear — proceed without asking.

--- FOLLOW-UP FILTER INHERITANCE (CRITICAL) ---
  When the user asks a follow-up question like "what did he return?", "show their orders",
  or "break it down by product", the SQL MUST carry forward ALL filters from the previous answer.

  RULE: If the prior answer was scoped to a specific entity (customer, product, region, rep, etc.),
  every follow-up query MUST include that same WHERE/JOIN filter — even if the user does not repeat it.

  Example:
    Previous answer → "John Smith (customer_id=27653) had the most returns."
    Follow-up → "What products did he return?"
    CORRECT SQL   → SELECT p.name, COUNT(*) FROM returns r JOIN ... WHERE c.customer_id = 27653 GROUP BY p.name
    INCORRECT SQL → SELECT p.name, COUNT(*) FROM returns r JOIN ... GROUP BY p.name  ← missing WHERE clause!

  The incorrect version would return ALL customers' returns grouped by product, not John Smith's.
  NEVER drop the scoping filter in a follow-up query.


  - PLURAL VS SINGULAR (CRITICAL): If the user asks for entities in plural (e.g., "Which suppliers have the most...", "What products are..."), DO NOT restrict the result to only the #1 absolute highest record (e.g., do not use `MAX()` or `rank=1`). Instead, assume they want a list and use `ORDER BY ... DESC LIMIT 10`. Only restrict to a single record if they explicitly use singular phrasing like "Which supplier...", "What is the best product...", or "Who is the top...".
  - DETERMINISTIC & COMPLETE RESULTS RULE: When explicitly asked for the single top/highest/lowest record (singular), NEVER use `LIMIT 1` (as it hides ties). Instead, use a subquery/CTE with WHERE to match the MAX value — this naturally returns ALL tied rows for the #1 spot. Example pattern:
    WITH totals AS (SELECT entity_id, SUM(sales_amount) AS s FROM orders GROUP BY entity_id)
    SELECT * FROM totals WHERE s = (SELECT MAX(s) FROM totals);
  - AGGREGATION RULE — TWO-STEP PATTERN (CRITICAL): When asked "which PRODUCT has the highest sales along with the SALESPERSON", you MUST use a two-step approach:
    STEP 1 — Find the product(s) with max total sales by grouping on product ONLY:
      WITH ProductTotals AS (
        SELECT p.product_name, SUM(o.sales_amount) AS total_product_sales
        FROM orders o JOIN products p ON o.product_id = p.product_id
        GROUP BY p.product_name
      ),
      TopProducts AS (
        SELECT product_name, total_product_sales FROM ProductTotals
        WHERE total_product_sales = (SELECT MAX(total_product_sales) FROM ProductTotals)
      )
    STEP 2 — For that product, show all sales reps and their individual contribution:
      SELECT tp.product_name, tp.total_product_sales, sr.sales_rep, SUM(o.sales_amount) AS rep_sales
      FROM orders o
      JOIN products p ON o.product_id = p.product_id
      JOIN sales_reps sr ON o.rep_id = sr.rep_id
      JOIN TopProducts tp ON p.product_name = tp.product_name
      GROUP BY tp.product_name, tp.total_product_sales, sr.sales_rep
      ORDER BY rep_sales DESC;
    NEVER group by (product + rep) in a single step when the question is about the top PRODUCT — that finds the top (product, rep) pair instead, which is WRONG.

--- DUPLICATE / EXACT MATCH QUESTIONS (CRITICAL) ---
  - When asked "are there any X with the same Y" or "do any rows share Y", you MUST use ROUND(column, 2) to avoid floating-point precision false negatives.
  - Use this HAVING pattern:
      SELECT ROUND(SUM(profit), 2) AS shared_value, COUNT(*) AS rep_count, STRING_AGG(sales_rep, ', ') AS reps
      FROM orders o JOIN sales_reps sr ON o.rep_id = sr.rep_id
      GROUP BY ROUND(SUM(profit), 2)
      HAVING COUNT(*) > 1
      ORDER BY shared_value DESC;
  - If the result is empty, clearly state "No sales reps share exactly the same total profit amount."
  - NEVER loop or retry more than once if the result is empty — accept the empty result and respond directly.

--- CRITICAL OUTPUT FORMATTING ---
YOU MUST ALWAYS end EVERY analytical response with the exact SQL query used to derive the answer. THIS IS NON-NEGOTIABLE. 
If the user asks "show the query" or asks a follow-up, you MUST output the SQL from your previous step.
Wrap the SQL EXACTLY in a markdown block at the very bottom of your response like this:
```sql
SELECT ...
```

══════════════════════════════════════════════
ABSOLUTE RULE — NUMBER REPORTING (DO NOT BREAK)
══════════════════════════════════════════════
You are STRICTLY FORBIDDEN from including any of the following in your response text:
- Specific numbers (e.g. two thousand three hundred, $2.3M)
- Counts (e.g. "one hundred and forty-two orders", "three suppliers")
- Percentages (e.g. "grew by fifteen percent")
- Currency amounts (e.g. "forty-five thousand dollars")
- Averages, totals, min, max, or any derived figures

If you must reference a year, write it in words: "twenty twenty-three".
If you must reference a small count like rows or top N, write it in words: "top ten".
Never write any currency, percentage, or business metric as a digit.

Your ONLY job in the response text is to:
1. Briefly explain what you searched for and which tables you used.
2. Describe the structure of the result (e.g. "grouped by month", "ranked by refund count").

The actual numbers will be injected automatically from the real database result.

CORRECT: "I queried the orders and payments tables, grouped by month, to show revenue over time."
WRONG:   "Revenue in January was $2.3M, growing 15% through March."
"""


# ═══════════════════════════════════════════════════════════════
# 4. LLM INITIALIZATION
# ═══════════════════════════════════════════════════════════════

llm = ChatGoogleGenerativeAI(
    model=config.MODEL_NAME,
    google_api_key=config.GOOGLE_API_KEY,
    temperature=0,
    timeout=120.0,       # Reduced from 600s — if it takes >2min something is wrong
    max_retries=5,
    model_kwargs={
        "thinking_config": {"thinking_budget": 0},  # Disable thinking — the #1 latency source
    },
    safety_settings={
        HarmCategory.HARM_CATEGORY_HARASSMENT: HarmBlockThreshold.BLOCK_NONE,
        HarmCategory.HARM_CATEGORY_HATE_SPEECH: HarmBlockThreshold.BLOCK_NONE,
        HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT: HarmBlockThreshold.BLOCK_NONE,
        HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT: HarmBlockThreshold.BLOCK_NONE,
    }
)

# ═══════════════════════════════════════════════════════════════
# 5. TOOL LIST & REACT AGENT
# ═══════════════════════════════════════════════════════════════

tools = [sql_query_tool, inspect_table_columns, policy_search_tool, visualization_tool]


# Module-level cache: holds the system prompt for the CURRENT agent run.
# Computed once per user query in run_agent/stream_agent, reused for every
# ReAct step so we don't pay the embedding + Supabase cost N times per query.
_current_system_prompt: str = ""


def _state_modifier(state):
    """Prepends the cached system prompt into the message state.
    
    The prompt is pre-computed in run_agent/stream_agent before invoking the
    agent, so this function is a cheap lookup, not a Supabase round-trip.
    """
    return [SystemMessage(content=_current_system_prompt)] + state["messages"]


agent = create_react_agent(
    model=llm,
    tools=tools,
    prompt=_state_modifier,
)

# Hard cap: prevents agent from looping more than 20 tool calls per request
_AGENT_CONFIG = {"recursion_limit": 20}

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


def _sanitize_history(messages: list) -> list:
    """
    Strip any trailing ToolMessages or AIMessages-with-tool_calls from the end
    of a message list so Gemini never sees an incomplete tool-call sequence.
    This is a last-resort guard; the primary protection is _compress_to_clean_pairs.
    """
    from langchain_core.messages import ToolMessage, AIMessage
    sanitized = list(messages)
    while sanitized:
        last = sanitized[-1]
        if isinstance(last, ToolMessage):
            sanitized.pop(); continue
        if isinstance(last, AIMessage) and getattr(last, "tool_calls", None):
            sanitized.pop(); continue
        break
    return sanitized


def _compress_to_clean_pairs(messages: list) -> list:
    """
    PRIMARY HISTORY STORE: Extract only (HumanMessage, final-AIMessage) pairs.

    Gemini forbids ToolMessages or AIMessages-with-tool_calls from appearing
    in the history of a NEW invocation — they are only valid WITHIN a single
    agent turn. Keeping them across turns always risks a 400 error.

    This function discards all intermediate tool-call messages and retains
    only the user question and the agent's final text answer, giving us a
    clean, guaranteed-valid conversation history for every new request.
    """
    from langchain_core.messages import ToolMessage, AIMessage
    clean: list = []
    for msg in messages:
        if isinstance(msg, HumanMessage):
            clean.append(msg)
        elif isinstance(msg, AIMessage) and not getattr(msg, "tool_calls", None):
            # Only keep final text-only AI responses
            if msg.content:
                clean.append(msg)
        # Discard: ToolMessage, AIMessage(tool_calls=[...]), SystemMessage
    return clean


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
    History stored as clean HumanMessage + final-AIMessage pairs only.
    """
    global _chat_history, _current_system_prompt
    try:
        _chat_history.append(HumanMessage(content=user_input))
        _trim_history()

        # Compute the system prompt ONCE here — includes the expensive
        # embedding API call + Supabase vector search + schema introspection.
        # _state_modifier reuses this cached value for every ReAct step.
        _current_system_prompt = get_system_prompt(user_input)

        result = agent.invoke({"messages": _chat_history}, config=_AGENT_CONFIG)

        response_messages = result.get("messages", [])
        ai_response = ""

        for msg in reversed(response_messages):
            if hasattr(msg, "content") and msg.content:
                text = _extract_text(msg.content).strip()
                if text and text != "None" and not getattr(msg, "tool_calls", None):
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

        # Store ONLY clean Human+FinalAI pairs — never ToolMessages or
        # intermediate AIMessage(tool_calls) — so the next turn always
        # starts with a Gemini-valid message sequence.
        if ai_response and ai_response != "No response generated.":
            _chat_history.append(AIMessage(content=ai_response))
        _chat_history = _compress_to_clean_pairs(_chat_history)
        _trim_history()
        return ai_response

    except Exception as e:
        # Roll back the HumanMessage we added so history stays clean
        _chat_history = _compress_to_clean_pairs(_chat_history)
        return (
            f"AGENT ERROR: Unable to process this request. "
            f"Please rephrase.\n(Debug: {e})"
        )


def stream_agent(user_input: str):
    """
    Yields intermediate steps from the agent for streaming UIs.

    History is stored as clean (HumanMessage, final-AIMessage) pairs only.
    Tool-call intermediates are used for the current invocation but never
    written to the persistent _chat_history, making Gemini 400 structurally
    impossible across turns.
    """
    global _chat_history, _current_system_prompt
    try:
        _chat_history.append(HumanMessage(content=user_input))
        _trim_history()

        # Compute the system prompt ONCE here — includes the expensive
        # embedding API call + Supabase vector search + schema introspection.
        # _state_modifier reuses this cached value for every ReAct step.
        _current_system_prompt = get_system_prompt(user_input)

        # Snapshot clean history as the input to the agent.
        input_messages = list(_chat_history)

        final_response = ""
        for step in agent.stream({"messages": input_messages}, config=_AGENT_CONFIG):
            yield step
            if "agent" in step:
                for msg in step["agent"].get("messages", []):
                    if getattr(msg, "content", "") and not getattr(msg, "tool_calls", None):
                        text = _extract_text(msg.content).strip()
                        if text and text != "None":
                            final_response = text

        # Stream finished cleanly — persist ONLY the final answer paired
        # with the user question. Everything else (ToolMessages, intermediate
        # AIMessage(tool_calls)) is intentionally discarded.
        if final_response:
            _chat_history.append(AIMessage(content=final_response))
        _chat_history = _compress_to_clean_pairs(_chat_history)
        _trim_history()

        if not final_response:
            final_response = "No response generated."

    except Exception as e:
        # Roll back to last clean state
        _chat_history = _compress_to_clean_pairs(_chat_history)
        yield {"error": str(e)}



def clear_memory():
    """Reset conversation memory and relationship cache."""
    global _chat_history, _relationships_cache
    _chat_history.clear()
    _relationships_cache = None  # Force reload from Supabase on next query