import sys
from pathlib import Path
sys.path.append(str(Path(__file__).resolve().parent))
import psycopg2
import config

def test_refund_query():
    conn = psycopg2.connect(**config.NEW_SUPABASE_DB_PARAMS)
    cur = conn.cursor()
    cur.execute("""
        WITH CategoryRefunds AS (
            SELECT
                c.category_name,
                SUM(r.refund) AS total_refund_amount
            FROM
                returns AS r
            JOIN
                order_items AS oi ON r.order_item_id = oi.order_item_id
            JOIN
                products AS p ON oi.product_id = p.product_id
            JOIN
                categories AS c ON p.category_id = c.category_id
            GROUP BY
                c.category_name
        )
        SELECT * FROM CategoryRefunds ORDER BY total_refund_amount DESC LIMIT 5;
    """)
    rows = cur.fetchall()
    print("Top 5 categories by refund:")
    for r in rows:
        print(r)
    cur.close()
    conn.close()

if __name__ == "__main__":
    test_refund_query()
