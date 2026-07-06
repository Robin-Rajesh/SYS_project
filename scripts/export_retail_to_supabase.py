"""
export_retail_to_supabase.py
============================
Exports all 12 retail CSVs into the new Supabase project.

Resilience features:
  - Fresh connection opened per table (avoids session-pooler idle timeout)
  - TCP keepalives (keepalives_idle=30s) prevent silent connection drops
  - Resume logic:
      * Count rows in DB vs CSV before loading
      * If counts match  -> SKIP  (already fully loaded)
      * If partial       -> TRUNCATE then reload
      * If empty         -> load fresh
  - Small tables  (<2 MB): COPY FROM STDIN
  - Large tables  (>=2 MB): chunked executemany, 5 000 rows/batch

Run:
    python scripts/export_retail_to_supabase.py
"""

import sys
import time
import csv
from pathlib import Path

import psycopg2
import psycopg2.extras

sys.path.append(str(Path(__file__).resolve().parent.parent))
import config

# ──────────────────────────────────────────────────────────────────────────────
# CONFIG
# ──────────────────────────────────────────────────────────────────────────────

RETAIL_DIR             = Path(__file__).resolve().parent.parent / "Retail dataset"
LARGE_TABLE_THRESHOLD  = 2.0      # MB — use COPY below, chunked INSERT above
CHUNK_SIZE             = 5_000    # rows per INSERT batch

# keepalives: ping every 30 s idle → prevents pooler dropping the connection
_CONN_PARAMS = {
    **config.NEW_SUPABASE_DB_PARAMS,
    "keepalives":          1,
    "keepalives_idle":     30,
    "keepalives_interval": 10,
    "keepalives_count":    5,
}

# ──────────────────────────────────────────────────────────────────────────────
# SCHEMA
# ──────────────────────────────────────────────────────────────────────────────

DROP_ORDER = [
    "returns", "shipments", "payments", "order_items",
    "orders", "employees", "products",
    "customers", "promotions", "suppliers", "stores", "categories",
]

CREATE_STATEMENTS = [
    """CREATE TABLE IF NOT EXISTS categories (
        category_id   INTEGER PRIMARY KEY,
        category_name TEXT    NOT NULL
    )""",
    """CREATE TABLE IF NOT EXISTS stores (
        store_id INTEGER PRIMARY KEY,
        city     TEXT    NOT NULL
    )""",
    """CREATE TABLE IF NOT EXISTS suppliers (
        supplier_id INTEGER PRIMARY KEY,
        country     TEXT    NOT NULL
    )""",
    """CREATE TABLE IF NOT EXISTS promotions (
        promotion_id INTEGER PRIMARY KEY,
        discount     NUMERIC NOT NULL
    )""",
    """CREATE TABLE IF NOT EXISTS customers (
        customer_id INTEGER PRIMARY KEY,
        city        TEXT,
        signup_date DATE
    )""",
    """CREATE TABLE IF NOT EXISTS employees (
        employee_id INTEGER PRIMARY KEY,
        store_id    INTEGER REFERENCES stores(store_id),
        salary      NUMERIC
    )""",
    """CREATE TABLE IF NOT EXISTS products (
        product_id  INTEGER PRIMARY KEY,
        category_id INTEGER REFERENCES categories(category_id),
        supplier_id INTEGER REFERENCES suppliers(supplier_id),
        price       NUMERIC NOT NULL
    )""",
    """CREATE TABLE IF NOT EXISTS orders (
        order_id     INTEGER PRIMARY KEY,
        customer_id  INTEGER REFERENCES customers(customer_id),
        store_id     INTEGER REFERENCES stores(store_id),
        order_date   DATE,
        promotion_id INTEGER REFERENCES promotions(promotion_id)
    )""",
    """CREATE TABLE IF NOT EXISTS order_items (
        order_item_id INTEGER PRIMARY KEY,
        order_id      INTEGER REFERENCES orders(order_id),
        product_id    INTEGER REFERENCES products(product_id),
        qty           INTEGER,
        price         NUMERIC
    )""",
    """CREATE TABLE IF NOT EXISTS payments (
        payment_id INTEGER PRIMARY KEY,
        order_id   INTEGER REFERENCES orders(order_id),
        amount     NUMERIC
    )""",
    """CREATE TABLE IF NOT EXISTS shipments (
        shipment_id INTEGER PRIMARY KEY,
        order_id    INTEGER REFERENCES orders(order_id),
        status      TEXT
    )""",
    """CREATE TABLE IF NOT EXISTS returns (
        return_id     INTEGER PRIMARY KEY,
        order_item_id INTEGER REFERENCES order_items(order_item_id),
        refund        NUMERIC
    )""",
]

TABLES = [
    ("categories",  "categories.csv"),
    ("stores",      "stores.csv"),
    ("suppliers",   "suppliers.csv"),
    ("promotions",  "promotions.csv"),
    ("customers",   "customers.csv"),
    ("employees",   "employees.csv"),
    ("products",    "products.csv"),
    ("orders",      "orders.csv"),
    ("order_items", "order_items.csv"),
    ("payments",    "payments.csv"),
    ("shipments",   "shipments.csv"),
    ("returns",     "returns.csv"),
]

# ──────────────────────────────────────────────────────────────────────────────
# HELPERS
# ──────────────────────────────────────────────────────────────────────────────

def new_conn():
    """Open a fresh connection with TCP keepalives."""
    return psycopg2.connect(**_CONN_PARAMS)


def file_mb(path: Path) -> float:
    return path.stat().st_size / 1_048_576


def count_csv_rows(path: Path) -> int:
    """Count data rows in CSV (excludes header)."""
    with open(path, "r", encoding="utf-8") as fh:
        return sum(1 for _ in fh) - 1


def db_row_count(table: str) -> int:
    """Return current row count for table (0 if table doesn't exist)."""
    try:
        conn = new_conn()
        cur  = conn.cursor()
        cur.execute(f"SELECT COUNT(*) FROM {table}")
        n = cur.fetchone()[0]
        cur.close(); conn.close()
        return n
    except Exception:
        return 0


def copy_fast(table: str, csv_path: Path) -> int:
    conn = new_conn()
    conn.autocommit = False
    cur  = conn.cursor()
    cur.execute("SET statement_timeout = 0;")
    with open(csv_path, "r", encoding="utf-8") as fh:
        cur.copy_expert(
            f"COPY {table} FROM STDIN WITH (FORMAT csv, HEADER true, NULL '')",
            fh,
        )
    rows = cur.rowcount
    conn.commit(); cur.close(); conn.close()
    return rows


def insert_chunked(table: str, csv_path: Path) -> int:
    """
    Load large CSV in chunks of CHUNK_SIZE.
    Opens a fresh connection per chunk-batch to avoid idle timeout.
    """
    total = 0
    with open(csv_path, "r", encoding="utf-8", newline="") as fh:
        reader  = csv.DictReader(fh)
        columns = reader.fieldnames
        ph      = ", ".join(["%s"] * len(columns))
        cols    = ", ".join(columns)
        sql     = f"INSERT INTO {table} ({cols}) VALUES ({ph})"

        chunk = []
        conn  = new_conn()
        conn.autocommit = False
        cur   = conn.cursor()
        cur.execute("SET statement_timeout = 0;")

        for row in reader:
            chunk.append([v if v != "" else None for v in row.values()])

            if len(chunk) >= CHUNK_SIZE:
                psycopg2.extras.execute_batch(cur, sql, chunk, page_size=500)
                conn.commit()
                total += len(chunk)
                print(f"      ... {total:,} rows committed", end="\r", flush=True)
                chunk = []

                # Recycle connection every 50 000 rows to beat idle timeout
                if total % 50_000 == 0:
                    cur.close(); conn.close()
                    conn = new_conn()
                    conn.autocommit = False
                    cur  = conn.cursor()
                    cur.execute("SET statement_timeout = 0;")

        if chunk:
            psycopg2.extras.execute_batch(cur, sql, chunk, page_size=500)
            conn.commit()
            total += len(chunk)

    cur.close(); conn.close()
    return total


# ──────────────────────────────────────────────────────────────────────────────
# SETUP  (idempotent — safe to re-run)
# ──────────────────────────────────────────────────────────────────────────────

def ensure_schema():
    """Drop & create tables only if ALL tables are empty (first run).
    On resume, tables that already have data are left untouched."""
    conn = new_conn()
    conn.autocommit = False
    cur  = conn.cursor()

    # Check if any table already has rows (resume mode)
    existing_rows = 0
    for table, _ in TABLES:
        try:
            cur.execute(f"SELECT COUNT(*) FROM {table}")
            existing_rows += cur.fetchone()[0]
        except Exception:
            pass

    if existing_rows == 0:
        print("  Fresh run — dropping and recreating all tables ...")
        for tbl in DROP_ORDER:
            cur.execute(f'DROP TABLE IF EXISTS "{tbl}" CASCADE')
        conn.commit()
        for stmt in CREATE_STATEMENTS:
            cur.execute(stmt)
        conn.commit()
        print("  All 12 tables created OK")
    else:
        print(f"  Resume mode — {existing_rows:,} rows already in DB, keeping existing tables.")
        # Ensure missing tables exist
        for stmt in CREATE_STATEMENTS:
            cur.execute(stmt)
        conn.commit()

    cur.close(); conn.close()


# ──────────────────────────────────────────────────────────────────────────────
# MAIN
# ──────────────────────────────────────────────────────────────────────────────

def main():
    print("=" * 62)
    print("  Retail Dataset -> Supabase Export  (resumable)")
    print("=" * 62)

    if not config.NEW_SUPABASE_DB_PARAMS:
        print("  ERROR: NEW_SUPABASE_DB_URL not set in .env")
        sys.exit(1)

    # -- test connection ------------------------------------------------------
    print(f"\nConnecting to {config.NEW_SUPABASE_DB_PARAMS['host']} ...")
    try:
        c = new_conn(); c.close()
        print("  Connection OK\n")
    except Exception as exc:
        print(f"  FAILED: {exc}"); sys.exit(1)

    # -- ensure schema --------------------------------------------------------
    ensure_schema()
    print()

    # -- load tables ----------------------------------------------------------
    total_rows = 0
    t_start    = time.perf_counter()

    for table, csv_file in TABLES:
        csv_path = RETAIL_DIR / csv_file
        if not csv_path.exists():
            print(f"  SKIP  {csv_file} not found")
            continue

        mb       = file_mb(csv_path)
        csv_rows = count_csv_rows(csv_path)
        db_rows  = db_row_count(table)

        # -- resume check -----------------------------------------------------
        if db_rows == csv_rows:
            print(f"  OK    {table:<15} {db_rows:>10,} rows  (already complete, skipping)")
            total_rows += db_rows
            continue

        if db_rows > 0:
            print(f"  RETRY {table:<15} partial ({db_rows:,}/{csv_rows:,}) — truncating and reloading ...")
            conn = new_conn(); conn.autocommit = True
            cur  = conn.cursor()
            cur.execute(f"TRUNCATE TABLE {table} CASCADE")
            cur.close(); conn.close()

        # -- load -------------------------------------------------------------
        method = "COPY" if mb < 2.0 else "chunked INSERT"
        print(f"  LOAD  {table:<15} [{mb:.1f} MB]  {csv_rows:,} rows  via {method} ...")
        t0 = time.perf_counter()

        try:
            if mb < 2.0:
                rows = copy_fast(table, csv_path)
            else:
                rows = insert_chunked(table, csv_path)

            elapsed = time.perf_counter() - t0
            print(f"\r  DONE  {table:<15} {rows:>10,} rows  ({elapsed:.1f}s)            ")
            total_rows += rows

        except Exception as exc:
            print(f"\n  ERROR on {table}: {exc}\n")

    elapsed_total = time.perf_counter() - t_start
    print("\n" + "=" * 62)
    print(f"  COMPLETE!  {total_rows:,} total rows  in  {elapsed_total:.1f}s")
    print("=" * 62)


if __name__ == "__main__":
    main()
