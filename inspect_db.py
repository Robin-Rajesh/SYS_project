import sqlite3
import os

db_path = "data/sales.db"
if os.path.exists(db_path):
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()
    cur.execute("SELECT name FROM sqlite_master WHERE type='table';")
    tables = cur.fetchall()
    print(f"Tables in {db_path}: {tables}")
    
    # Check if there is a 'metadata' table
    cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name LIKE '%meta%';")
    meta_tables = cur.fetchall()
    print(f"Metadata tables: {meta_tables}")
    
    conn.close()
else:
    print(f"{db_path} not found.")
