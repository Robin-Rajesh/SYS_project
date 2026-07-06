import sys
import time
from pathlib import Path
sys.path.append(str(Path(__file__).resolve().parent))

print("Importing modules...", flush=True)
import agent

def test_stream():
    query = "Which product categories have the lowest sales?"
    print(f"\n--- Testing Streaming LLM Agent Response for '{query}' ---", flush=True)
    try:
        t0 = time.time()
        for step in agent.stream_agent(query):
            print(f"[{time.time()-t0:.2f}s] STEP YIELDED:", flush=True)
            if "agent" in step:
                print("  -> AGENT YIELD:", flush=True)
                for msg in step["agent"].get("messages", []):
                    if hasattr(msg, "tool_calls") and msg.tool_calls:
                        print(f"     Tool Calls: {msg.tool_calls}", flush=True)
                    if hasattr(msg, "content") and msg.content:
                        print(f"     Content: {msg.content[:200]}...", flush=True)
            elif "tools" in step:
                print("  -> TOOLS YIELD:", flush=True)
                for msg in step["tools"].get("messages", []):
                    print(f"     Tool Result: {msg.content[:200]}...", flush=True)
            else:
                print(f"  -> OTHER: {step}", flush=True)
        print(f"Finished in {time.time()-t0:.2f}s", flush=True)
    except Exception as e:
        print(f"Error: {e}", flush=True)

if __name__ == "__main__":
    test_stream()
