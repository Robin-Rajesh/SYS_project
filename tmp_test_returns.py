import sys
from pathlib import Path
sys.path.append(str(Path(__file__).resolve().parent))
import psycopg2
import config

def test_returns():
    conn = psycopg2.connect(**config.NEW_SUPABASE_DB_PARAMS)
    cur = conn.cursor()
    cur.execute("""
        SELECT r.return_id, oi.qty 
        FROM returns r
        JOIN order_items oi ON r.order_item_id = oi.order_item_id
        LIMIT 10;
    """)
    rows = cur.fetchall()
    print("Sample returns and their original quantities:")
    for r in rows:
        print(f"Return ID: {r[0]}, Qty in Order Item: {r[1]}")
    cur.close()
    conn.close()

if __name__ == "__main__":
    test_returns()
