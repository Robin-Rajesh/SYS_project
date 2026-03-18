"""
agent.py — LangChain ReAct Agent Powered by Google Gemini 1.5 Flash
====================================================================
Uses langgraph's create_react_agent (the modern LangChain approach)
to build a tool-calling agent with:
  - Gemini 1.5 Flash LLM (temperature=0)
  - Three tools: sql_query_tool, policy_search_tool, visualization_tool
  - A detailed system prompt preventing hallucination
  - Conversation memory (last 5 exchanges kept in a message list)
  - A single entry point: run_agent(user_input) → str
"""

from langchain_google_genai import ChatGoogleGenerativeAI
from langgraph.prebuilt import create_react_agent
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage

# Import project config and all three tools
import config
from tools.sql_tool import sql_query_tool
from tools.rag_tool import policy_search_tool
from tools.visualizer_tool import visualization_tool

# ═══════════════════════════════════════════════════════════════
# 1. DYNAMIC SYSTEM PROMPT
# ═══════════════════════════════════════════════════════════════

def get_system_prompt() -> str:
    """
    Generates the system prompt dynamically, injecting the schema 
    of whatever database is currently connected.
    """
    from tools.sql_tool import get_schema
    current_schema = get_schema()
    
    return f"""\
You are an expert Data Analyst AI assistant with access to three tools:

1. sql_query_tool: Query the connected SQL database using SELECT statements only.
   Never guess column names. Here is the exact schema of the database you are querying:
   
{current_schema}

2. policy_search_tool: Search internal policy documents, discount
   approval matrices, and catalogs. Use this for any policy or product questions.

3. visualization_tool: Generate and save charts. Always get data from
   sql_query_tool first, then pass it to this tool as a JSON string.

STRICT RULES YOU MUST FOLLOW:
- Never invent or hallucinate data, numbers, metrics, or policy rules.
- If data is unavailable, respond exactly: "DATA UNAVAILABLE: [reason]"
- For hybrid questions (data + policy), ALWAYS call BOTH sql_query_tool
  AND policy_search_tool before answering.
- When user asks for a chart, ALWAYS call sql_query_tool first to get
  data, then call visualization_tool with that data.
- Think step by step. State your plan before executing tools.
- Format your final answer clearly with sections if needed.
"""

# ═══════════════════════════════════════════════════════════════
# 2. LLM INITIALIZATION
# ═══════════════════════════════════════════════════════════════
# temperature=0 produces deterministic, factual responses.

llm = ChatGoogleGenerativeAI(
    model=config.MODEL_NAME,
    google_api_key=config.GOOGLE_API_KEY,
    temperature=0,
    timeout=600.0,
    max_retries=5,
)

# ═══════════════════════════════════════════════════════════════
# 3. TOOL LIST
# ═══════════════════════════════════════════════════════════════

tools = [sql_query_tool, policy_search_tool, visualization_tool]

# ═══════════════════════════════════════════════════════════════
# 4. REACT AGENT (langgraph)
# ═══════════════════════════════════════════════════════════════

def _state_modifier(state):
    """Dynamically prepends the freshest system prompt into the message state."""
    return [SystemMessage(content=get_system_prompt())] + state["messages"]

agent = create_react_agent(
    model=llm,
    tools=tools,
    prompt=_state_modifier,
)

# ═══════════════════════════════════════════════════════════════
# 5. CONVERSATION MEMORY (manual window of last 5 exchanges)
# ═══════════════════════════════════════════════════════════════
# We maintain a simple list of messages and trim to the last k
# exchanges (pairs of Human + AI messages) before each call.

_chat_history: list = []
_MEMORY_WINDOW = 10   # keep last 10 user/assistant pairs


def _trim_history():
    """Keep only the last _MEMORY_WINDOW pairs of messages."""
    global _chat_history
    # Each exchange = 1 HumanMessage + 1 AIMessage = 2 messages
    max_messages = _MEMORY_WINDOW * 2
    if len(_chat_history) > max_messages:
        _chat_history = _chat_history[-max_messages:]


# ═══════════════════════════════════════════════════════════════
# 6. PUBLIC ENTRY POINT
# ═══════════════════════════════════════════════════════════════

def _extract_text(content) -> str:
    """Safely extracts text from the LLM's content field, which might be a list of dicts."""
    if isinstance(content, list):
        texts = []
        for item in content:
            if isinstance(item, dict) and 'text' in item:
                texts.append(item['text'])
            elif isinstance(item, str):
                texts.append(item)
        return " ".join(texts)
    return str(content)

def run_agent(user_input: str) -> str:
    """
    Send a user message to the agent and return its text response.
    Wraps the call in try/except so unhandled errors produce a
    friendly message instead of a raw traceback.
    """
    global _chat_history
    try:
        # Append the new user message to history
        _chat_history.append(HumanMessage(content=user_input))
        _trim_history()

        # Invoke the agent with the full message history
        result = agent.invoke({"messages": _chat_history})

        # Extract the final AI response
        response_messages = result.get("messages", [])
        ai_response = ""
        
        # Iterate backwards to find the first AIMessage with content
        # Sometimes the model returns a tool call message and then a final message
        for msg in reversed(response_messages):
            if hasattr(msg, "content") and msg.content:
                text = _extract_text(msg.content).strip()
                if text and text != "None":
                    ai_response = text
                    break

        if not ai_response:
            # Fallback: Check if any message contains content
            all_content = [
                _extract_text(m.content) 
                for m in response_messages 
                if hasattr(m, "content") and m.content
            ]
            if all_content:
                # Find the longest content block (likely the HTML report)
                ai_response = max(all_content, key=len)
            else:
                with open("outputs/debug_agent.txt", "w", encoding="utf-8") as f:
                    f.write(f"Result dump:\n{result}\n\n")
                ai_response = "No response generated."

        # Store the AI response in history
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
        # Append the new user message to history
        _chat_history.append(HumanMessage(content=user_input))
        _trim_history()

        final_response = ""
        for step in agent.stream({"messages": _chat_history}):
            yield step
            
            # Capture the final AI message content to store in memory
            if "agent" in step:
                msg = step["agent"]["messages"][-1]
                if getattr(msg, "content", ""):
                    final_response = _extract_text(msg.content)

        if not final_response:
            final_response = "No response generated."

        # Store the AI response in history
        _chat_history.append(AIMessage(content=final_response))
        _trim_history()

    except Exception as e:
        yield {"error": str(e)}


def clear_memory():
    """Reset conversation memory — called by the 'clear' command."""
    global _chat_history
    _chat_history.clear()
