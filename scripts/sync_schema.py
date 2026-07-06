"""
sync_schema.py — Supabase Schema Intelligence Sync (New Retail Project)
========================================================================
Run once on first deployment, or after any schema change:
    python scripts/sync_schema.py

This script targets the NEW Supabase retail project and:
  1. Enables the pgvector extension.
  2. Creates table_embeddings  (VECTOR(1536) + HNSW index + column_hash).
     Embedding model: gemini-embedding-001 with MRL @ 1536-dim.
  3. Creates schema_relationships table + index.
  4. Introspects FK relationships LIVE from information_schema
     (no hardcoded JSON — always accurate for the retail schema).
  5. Upserts all FK rows into schema_relationships.
"""

import sys
from pathlib import Path
import psycopg2
import psycopg2.extras

sys.path.append(str(Path(__file__).resolve().parent.parent))
import config


def sync_schema():
    print("=" * 60)
    print("  Schema Sync -> New Retail Supabase Project")
    print("=" * 60)

    # ── connect ──────────────────────────────────────────────────────────────
    print(f"\n[1/4] Connecting to {config.NEW_SUPABASE_DB_PARAMS['host']} ...")
    try:
        conn = psycopg2.connect(**config.NEW_SUPABASE_DB_PARAMS)
        conn.autocommit = True          # DDL statements don't need explicit commit
        cur = conn.cursor()
        cur.execute("SELECT version();")
        pg_ver = cur.fetchone()[0].split(",")[0]
        print(f"      Connected OK  ({pg_ver})")
    except Exception as exc:
        print(f"  FAILED: {exc}")
        raise Exception(exc)

    # ── 1. Enable pgvector ───────────────────────────────────────────────────
    print("\n[2/4] Enabling pgvector extension ...")
    try:
        cur.execute("CREATE EXTENSION IF NOT EXISTS vector;")
        print("      pgvector enabled OK")
    except Exception as exc:
        print(f"      WARNING: {exc}")

    # ── 2. Create table_embeddings ───────────────────────────────────────────
    print("\n[3/4] Creating meta-tables ...")
    try:
        cur.execute("""
            CREATE TABLE IF NOT EXISTS table_embeddings (
                table_name  TEXT PRIMARY KEY,
                description TEXT,
                embedding   VECTOR(1536),
                column_hash TEXT,
                updated_at  TIMESTAMPTZ DEFAULT now()
            );
        """)
        cur.execute("""
            CREATE INDEX IF NOT EXISTS idx_table_embeddings_hnsw
            ON table_embeddings
            USING hnsw (embedding vector_cosine_ops);
        """)
        print("      table_embeddings + HNSW index  OK")
    except Exception as exc:
        print(f"  ERROR creating table_embeddings: {exc}")
        sys.exit(1)

    # ── 3. Create schema_relationships ───────────────────────────────────────
    try:
        cur.execute("""
            CREATE TABLE IF NOT EXISTS schema_relationships (
                id          SERIAL PRIMARY KEY,
                from_table  TEXT NOT NULL,
                from_col    TEXT NOT NULL,
                to_table    TEXT NOT NULL,
                to_col      TEXT NOT NULL
            );
        """)
        cur.execute("""
            CREATE INDEX IF NOT EXISTS idx_schema_rel_from
            ON schema_relationships (from_table);
        """)
        # Wipe before repopulating to stay idempotent
        cur.execute("TRUNCATE TABLE schema_relationships RESTART IDENTITY;")
        print("      schema_relationships + index   OK")
    except Exception as exc:
        print(f"  ERROR creating schema_relationships: {exc}")
        sys.exit(1)

    # ── 4. Introspect FKs from live information_schema ────────────────────────
    print("\n[4/4] Introspecting FK relationships from information_schema ...")
    try:
        cur.execute("""
            SELECT
                tc.table_name        AS from_table,
                kcu.column_name      AS from_col,
                ccu.table_name       AS to_table,
                ccu.column_name      AS to_col
            FROM information_schema.table_constraints   AS tc
            JOIN information_schema.key_column_usage    AS kcu
                ON tc.constraint_name = kcu.constraint_name
               AND tc.table_schema   = kcu.table_schema
            JOIN information_schema.constraint_column_usage AS ccu
                ON ccu.constraint_name = tc.constraint_name
               AND ccu.table_schema    = tc.table_schema
            WHERE tc.constraint_type = 'FOREIGN KEY'
              AND tc.table_schema    = 'public'
            ORDER BY tc.table_name, kcu.column_name;
        """)
        fk_rows = cur.fetchall()

        if not fk_rows:
            print("      WARNING: no FK rows found — run export first!")
        else:
            psycopg2.extras.execute_batch(
                cur,
                """
                INSERT INTO schema_relationships (from_table, from_col, to_table, to_col)
                VALUES (%s, %s, %s, %s)
                """,
                fk_rows,
            )
            print(f"      Synced {len(fk_rows)} FK relationships OK")
            for row in fk_rows:
                print(f"        {row[0]}.{row[1]}  ->  {row[2]}.{row[3]}")

    except Exception as exc:
        print(f"  ERROR syncing FK relationships: {exc}")

    cur.close()
    conn.close()
    print("\n  Schema sync complete!")


if __name__ == "__main__":
    sync_schema()
