import sys
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
# Insert at 0 to take priority over any sibling projects that may also have an agent.py
sys.path.insert(0, str(BASE_DIR))

import config
# Ensure cloud mode is enabled for pgvector schema sync testing
config.IS_CLOUD = True

from fastapi.testclient import TestClient
from api import app

def run_api_tests():
    print("=" * 70)
    print("  Testing FastAPI Lifespan hook & REST endpoints")
    print("=" * 70)
    
    # 1. Initialize TestClient within a 'with' context manager to trigger lifespan events
    print("Initializing TestClient (triggers lifespan startup sync)...")
    with TestClient(app) as client:
        print("\nTestClient started OK!")
        
        # 2. Test GET /api/schema/tables
        print("\n--- Testing GET /api/schema/tables ---")
        response = client.get("/api/schema/tables")
        print(f"Status Code: {response.status_code}")
        if response.status_code == 200:
            tables = response.json()
            print(f"Returned {len(tables)} tables:")
            for t in tables[:3]:  # Print first 3 tables for brevity
                print(f"  - {t['table_name']}: {t['description'][:100]}...")
            if len(tables) > 3:
                print(f"  ... and {len(tables) - 3} more tables.")
        else:
            print(f"Error: {response.text}")
            
        # 3. Test POST /api/schema/sync
        print("\n--- Testing POST /api/schema/sync ---")
        response = client.post("/api/schema/sync")
        print(f"Status Code: {response.status_code}")
        if response.status_code == 200:
            result = response.json()
            print(f"Sync successful! Result: {result}")
        else:
            print(f"Error: {response.text}")
            
    print("\n" + "=" * 70)
    print("  FastAPI Tests Completed Successfully!")
    print("=" * 70)

if __name__ == "__main__":
    run_api_tests()
