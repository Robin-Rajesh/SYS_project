import sys
from pathlib import Path
import os

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))  # Ensure this project takes priority

import config
from tools.schema_retriever import retrieve_resolved_tables, _embed_query
import psycopg2

def run_tests():
    # Ensure cloud mode is enabled for the test so we hit pgvector
    config.IS_CLOUD = True
    
    # Let's inspect the similarity scores of all tables for a few queries
    queries = [
        "Show me product categories and their average prices.",
        "List our customers who made orders.",
        "How many shipments are pending?",
        "Find suppliers in Canada.",
    ]
    
    conn = psycopg2.connect(**config.NEW_SUPABASE_DB_PARAMS)
    cur = conn.cursor()
    print("=" * 70)
    print("  Testing Schema Retriever & Similarity Scores")
    print("=" * 70)
    
    # Print current pruning threshold
    threshold = float(os.getenv("PRUNING_THRESHOLD", "0.30"))
    print(f"Active PRUNING_THRESHOLD: {threshold}\n")
    
    for q in queries:
        print(f"QUERY: \"{q}\"")
        # Get query embedding
        query_vec = _embed_query(q)
        # Query similarities
        cur.execute("""
            SELECT table_name, 1 - (embedding <=> %s::vector) AS similarity
            FROM table_embeddings
            ORDER BY similarity DESC
        """, (str(query_vec),))
        
        rows = cur.fetchall()
        print("  All Similarity Scores:")
        for r in rows:
            print(f"    - {r[0]:15s}: {r[1]:.4f}")
            
        resolved = retrieve_resolved_tables(q)
        print(f"  Resolved Tables: {resolved}")
        print("-" * 70)
        
    cur.close()
    conn.close()

if __name__ == "__main__":
    run_tests()
