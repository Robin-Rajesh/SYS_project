import sys
from pathlib import Path
sys.path.append(str(Path(__file__).resolve().parent))
import psycopg2
import config

def test_returns_correctly():
    conn = psycopg2.connect(**config.NEW_SUPABASE_DB_PARAMS)
    cur = conn.cursor()
    cur.execute("""
        WITH sales AS (
            SELECT p.category_id, SUM(oi.qty) as sold
            FROM order_items oi
            JOIN products p ON oi.product_id = p.product_id
            GROUP BY 1
        ),
        returns_correct AS (
            SELECT p.category_id, SUM(oi.qty) as returned
            FROM returns r
            JOIN order_items oi ON r.order_item_id = oi.order_item_id
            JOIN products p ON oi.product_id = p.product_id
            GROUP BY 1
        )
        SELECT s.category_id, c.category_name, r.returned, s.sold, 
               (r.returned::numeric / s.sold) as return_rate
        FROM sales s
        JOIN returns_correct r ON s.category_id = r.category_id
        JOIN categories c ON s.category_id = c.category_id
        WHERE c.category_name = 'Cat_11'
    """)
    rows = cur.fetchall()
    for r in rows:
        print(r)
    cur.close()
    conn.close()

if __name__ == "__main__":
    test_returns_correctly()
