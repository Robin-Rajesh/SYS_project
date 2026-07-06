import sys
import time
from pathlib import Path
sys.path.append(str(Path(__file__).resolve().parent))

print("Importing modules...", flush=True)
import agent
from tools.schema_retriever import get_resolved_schema_context

def test_speed():
    query = "Which product categories have the lowest sales?"
    
    print("\n--- Testing Schema Retrieval ---", flush=True)
    t0 = time.time()
    schema = get_resolved_schema_context(query)
    t1 = time.time()
    print(f"Schema Retrieval took: {t1 - t0:.2f} seconds", flush=True)
    
    print("\n--- Testing LLM Agent Response ---", flush=True)
    try:
        response = agent.run_agent(query)
        t2 = time.time()
        print(f"LLM Agent took: {t2 - t1:.2f} seconds", flush=True)
        print(f"\nResponse:\n{response}", flush=True)
    except Exception as e:
        print(f"Error: {e}", flush=True)

if __name__ == "__main__":
    test_speed()
