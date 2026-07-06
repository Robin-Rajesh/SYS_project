import sys
from pathlib import Path
sys.path.append(str(Path(__file__).resolve().parent))
from tools.sql_tool import _validate_and_fix_sql

sql = """
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
"""

validated_sql, corrections = _validate_and_fix_sql(sql)
print("Original:", sql)
print("Validated:", validated_sql)
print("Corrections:", corrections)
