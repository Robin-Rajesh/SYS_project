import sys
from pathlib import Path
sys.path.append(str(Path(__file__).resolve().parent))
import psycopg2
import config

def test_sql():
    conn = psycopg2.connect(**config.NEW_SUPABASE_DB_PARAMS)
    cur = conn.cursor()
    try:
        cur.execute("""
        SELECT
          c.category_name,
          SUM(oi.qty * oi.price) AS total_sales
        FROM order_items AS oi
        JOIN products AS p
          ON oi.product_id = p.product_id
        JOIN categories AS c
          ON p.category_id = c.category_id
        GROUP BY
          c.category_name
        ORDER BY
          total_sales ASC;
        """)
        rows = cur.fetchall()
        print("Success!", rows[:2])
    except Exception as e:
        print("Error:", e)
    cur.close()
    conn.close()

if __name__ == "__main__":
    test_sql()
