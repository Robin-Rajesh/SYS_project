import sqlite3, os

db_path = "data/sales_normalized_1_1.db"
if not os.path.exists(db_path):
    print("NOT FOUND — file does not exist at", os.path.abspath(db_path))
else:
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()
    cur.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")
    tables = [r[0] for r in cur.fetchall()]
    print("TABLES:", tables)
    for t in tables:
        cur.execute(f"PRAGMA table_info({t})")
        cols = cur.fetchall()
        cur.execute(f"PRAGMA foreign_key_list({t})")
        fks = cur.fetchall()
        print(f"\n--- {t} ---")
        for c in cols:
            pk = " [PK]" if c[5] else ""
            nn = " NOT NULL" if c[3] else ""
            print(f"  {c[1]}  {c[2]}{pk}{nn}")
        if fks:
            for fk in fks:
                print(f"  FK: {fk[3]} -> {fk[2]}.{fk[4]}")
    conn.close()
