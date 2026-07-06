import sys
from pathlib import Path
sys.path.append(str(Path(__file__).resolve().parent))
import psycopg2
import config

query = """
WITH monthly_gross AS (
    SELECT
        date_trunc('month', o.order_date) AS month,
        SUM(p.amount) AS gross_revenue
    FROM payments AS p
    JOIN orders AS o
        ON p.order_id = o.order_id
    GROUP BY 1
),
monthly_refunds AS (
    SELECT
        date_trunc('month', o.order_date) AS month,
        SUM(r.refund) AS total_refunds
    FROM returns AS r
    JOIN order_items AS oi
        ON r.order_item_id = oi.order_item_id
    JOIN orders AS o
        ON oi.order_id = o.order_id
    GROUP BY 1
)
SELECT
    to_char(g.month, 'YYYY-MM') AS month,
    g.gross_revenue,
    COALESCE(r.total_refunds, 0) AS total_refunds,
    g.gross_revenue - COALESCE(r.total_refunds, 0) AS net_revenue
FROM monthly_gross g
LEFT JOIN monthly_refunds r ON g.month = r.month
ORDER BY g.month
LIMIT 5;
"""

def test_query():
    conn = psycopg2.connect(**config.NEW_SUPABASE_DB_PARAMS)
    cur = conn.cursor()
    cur.execute(query)
    rows = cur.fetchall()
    for r in rows:
        print(r)
    cur.close()
    conn.close()

if __name__ == "__main__":
    test_query()
