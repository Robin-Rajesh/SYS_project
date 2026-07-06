import psycopg2
import time

params = dict(
    host="aws-1-ap-southeast-1.pooler.supabase.com",
    port=6543,
    dbname="postgres",
    user="postgres.opleilhqildaykfwhmwi",
    password="S9UB-fMiG4c-pZp",
    sslmode="require",
    connect_timeout=15,
)

print("Testing port 6543 (transaction pooler)...")
t = time.time()
try:
    conn = psycopg2.connect(**params)
    cur = conn.cursor()
    cur.execute("SELECT tablename FROM pg_tables WHERE schemaname='public'")
    tables = [r[0] for r in cur.fetchall()]
    print(f"Connected OK in {time.time()-t:.1f}s")
    print(f"Tables ({len(tables)}):", tables)
    conn.close()
except Exception as e:
    print(f"FAILED in {time.time()-t:.1f}s: {e}")
