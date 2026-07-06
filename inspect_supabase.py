import sys
import psycopg2
import config

def inspect_supabase():
    print("Connecting to Supabase...")
    try:
        conn = psycopg2.connect(**config.NEW_SUPABASE_DB_PARAMS)
        cur = conn.cursor()
        
        print("\n--- TABLE EMBEDDINGS ---")
        cur.execute("SELECT table_name, description, column_hash, LENGTH(embedding::text) FROM table_embeddings ORDER BY table_name")
        rows = cur.fetchall()
        for row in rows:
            print(f"Table: {row[0]}")
            print(f"  Hash: {row[2]}")
            print(f"  Vector Length: {row[3]} chars")
            print(f"  Description: {row[1]}")
            print("-" * 50)
            
        print("\n--- SCHEMA RELATIONSHIPS ---")
        cur.execute("SELECT from_table, from_col, to_table, to_col FROM schema_relationships ORDER BY from_table")
        fk_rows = cur.fetchall()
        for fk in fk_rows:
            print(f"  {fk[0]}.{fk[1]} -> {fk[2]}.{fk[3]}")
            
        cur.close()
        conn.close()
    except Exception as e:
        print("Error:", e)

if __name__ == "__main__":
    inspect_supabase()
