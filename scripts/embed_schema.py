"""
embed_schema.py — Smart Schema Embedding Sync
==============================================
Embeds each retail table's schema description into the table_embeddings
vector store on Supabase. Uses MD5 hashing to skip unchanged tables.

Algorithm per table:
  1. Introspect columns + FKs from information_schema (live)
  2. Build canonical string: sorted column names + sorted FK refs
  3. Compute MD5 of that string -> new_hash
  4. Query:  SELECT column_hash FROM table_embeddings WHERE table_name = ?
  5. If hash matches stored hash  -> SKIP  (no embedding cost)
  6. Else:
       a. Build natural-language description
       b. Embed with gemini-embedding-001 (MRL @ 1536-dim via Google API)
       c. UPSERT into table_embeddings

Run:
    python scripts/embed_schema.py

Re-run freely — only changed tables are re-embedded.
"""

import sys
import hashlib
import time
from pathlib import Path
from datetime import datetime, timezone

import psycopg2
import psycopg2.extras

sys.path.append(str(Path(__file__).resolve().parent.parent))
import config

# ──────────────────────────────────────────────────────────────────────────────
# Embedding helper (google.genai — the new, actively maintained SDK)
# ──────────────────────────────────────────────────────────────────────────────
import google.genai as genai

_genai_client = genai.Client(api_key=config.GOOGLE_API_KEY)

def _embed(text: str) -> list[float]:
    """Embed text using gemini-embedding-001 with MRL at config.EMBEDDING_DIMENSIONS."""
    result = _genai_client.models.embed_content(
        model=config.EMBEDDING_MODEL,
        contents=text,
        config={"output_dimensionality": config.EMBEDDING_DIMENSIONS},
    )
    return result.embeddings[0].values


# ──────────────────────────────────────────────────────────────────────────────
# Schema introspection helpers
# ──────────────────────────────────────────────────────────────────────────────

def get_table_columns(cur, table: str) -> list[dict]:
    """Return list of {column_name, data_type, is_nullable} for a table."""
    cur.execute("""
        SELECT column_name, data_type, is_nullable
        FROM information_schema.columns
        WHERE table_schema = 'public'
          AND table_name   = %s
        ORDER BY ordinal_position
    """, (table,))
    return [{"name": r[0], "type": r[1], "nullable": r[2]} for r in cur.fetchall()]


def get_table_fks(cur, table: str) -> list[dict]:
    """Return list of {from_col, to_table, to_col} FK refs for a table."""
    cur.execute("""
        SELECT
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
          AND tc.table_name      = %s
        ORDER BY kcu.column_name
    """, (table,))
    return [{"from_col": r[0], "to_table": r[1], "to_col": r[2]} for r in cur.fetchall()]


def get_all_table_names(cur) -> list[str]:
    """Return all user-defined tables in the public schema (excluding meta-tables)."""
    cur.execute("""
        SELECT table_name
        FROM information_schema.tables
        WHERE table_schema = 'public'
          AND table_type   = 'BASE TABLE'
          AND table_name NOT IN ('table_embeddings', 'schema_relationships',
                                  'langchain_pg_collection', 'langchain_pg_embedding')
        ORDER BY table_name
    """)
    return [r[0] for r in cur.fetchall()]


# ──────────────────────────────────────────────────────────────────────────────
# Hash computation
# ──────────────────────────────────────────────────────────────────────────────

def compute_schema_hash(columns: list[dict], fks: list[dict]) -> str:
    """
    MD5 of a canonical representation:
        col1:type1|col2:type2|...|FK:from_col->to_table.to_col|...
    Sorted so order doesn't matter.
    """
    col_parts = sorted([f"{c['name']}:{c['type']}" for c in columns])
    fk_parts  = sorted([f"FK:{f['from_col']}->{f['to_table']}.{f['to_col']}" for f in fks])
    canonical = "|".join(col_parts + fk_parts)
    return hashlib.md5(canonical.encode()).hexdigest()


# ──────────────────────────────────────────────────────────────────────────────
# Natural-language description builder
# ──────────────────────────────────────────────────────────────────────────────

def generate_llm_description(table: str, columns: list[dict], sample_rows: list) -> str | None:
    """
    Asks Gemini to write a 2-sentence business description of the table.
    """
    col_str = "\n".join([f"  - {c['name']} ({c['type']})" for c in columns])
    rows_str = "\n".join([str(row) for row in sample_rows]) if sample_rows else "No rows found."
    
    prompt = f"""You are an expert business database analyst.
Write a concise, exactly 2-sentence business description of what the following database table stores and what it represents in a retail analytics context.
Do not include technical columns list or markdown code formatting in your output. Just return the 2 sentences.

TABLE NAME: {table}

COLUMNS:
{col_str}

SAMPLE ROWS:
{rows_str}

Description:"""
    
    try:
        from langchain_google_genai import ChatGoogleGenerativeAI, HarmCategory, HarmBlockThreshold
        llm = ChatGoogleGenerativeAI(
            model=config.MODEL_NAME,
            google_api_key=config.GOOGLE_API_KEY,
            temperature=0,
            timeout=15.0,
            safety_settings={
                HarmCategory.HARM_CATEGORY_HARASSMENT: HarmBlockThreshold.BLOCK_NONE,
                HarmCategory.HARM_CATEGORY_HATE_SPEECH: HarmBlockThreshold.BLOCK_NONE,
                HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT: HarmBlockThreshold.BLOCK_NONE,
                HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT: HarmBlockThreshold.BLOCK_NONE,
            }
        )
        res = llm.invoke(prompt)
        desc = res.content.strip()
        if desc:
            return desc
    except Exception as e:
        print(f" (LLM description failed: {e}. Falling back to default)", end="")
    return None


def build_description(table: str, columns: list[dict], fks: list[dict]) -> str:
    """
    Builds a rich description capturing the table's business role,
    all columns with PK/FK annotations, and the full FK join chain.
    This ensures embeddings score semantically for multi-hop join queries
    (e.g. 'total refund per customer' resolves customers via returns->order_items->orders->customers).
    """
    fk_map = {f["from_col"]: f for f in fks}
    col_descs = []
    for col in columns:
        name = col["name"]
        dtype = col["type"]
        if name.endswith("_id") and name == f"{table[:-1]}_id" or name == f"{table}_id":
            note = "PK"
        elif name in fk_map:
            fk = fk_map[name]
            note = f"FK->{fk['to_table']}.{fk['to_col']}"
        else:
            note = dtype
        col_descs.append(f"{name} ({note})")

    fk_summary = ""
    join_chain = ""
    if fks:
        refs = [f"{f['from_col']} references {f['to_table']}" for f in fks]
        fk_summary = f" Foreign keys: {', '.join(refs)}."
        targets = [f['to_table'] for f in fks]
        join_chain = (
            f" To query across tables, join {table} with "
            + ", ".join(targets) + "."
        )

    return (
        f"Table `{table}` stores {table.replace('_', ' ')} data. "
        f"It has {len(columns)} columns: {', '.join(col_descs)}.{fk_summary}{join_chain}"
    )


# ──────────────────────────────────────────────────────────────────────────────
# Stored-hash lookup
# ──────────────────────────────────────────────────────────────────────────────

def get_stored_hash(cur, table: str) -> str | None:
    cur.execute(
        "SELECT column_hash FROM table_embeddings WHERE table_name = %s",
        (table,),
    )
    row = cur.fetchone()
    return row[0] if row else None


# ──────────────────────────────────────────────────────────────────────────────
# Main sync function
# ──────────────────────────────────────────────────────────────────────────────

def sync_embeddings():
    print("=" * 62)
    print("  Schema Embedding Sync (MD5 hash-based, skips unchanged)")
    print("=" * 62)

    # -- connect --------------------------------------------------------------
    print(f"\nConnecting to {config.NEW_SUPABASE_DB_PARAMS['host']} ...")
    try:
        conn = psycopg2.connect(**config.NEW_SUPABASE_DB_PARAMS)
        conn.autocommit = False
        cur = conn.cursor()
        cur.execute("SELECT version();")
        pg_ver = cur.fetchone()[0].split(",")[0]
        print(f"  Connected OK  ({pg_ver})\n")
    except Exception as exc:
        print(f"  FAILED: {exc}")
        raise Exception(exc)

    # -- get table list -------------------------------------------------------
    tables = get_all_table_names(cur)
    print(f"  Found {len(tables)} tables: {', '.join(tables)}\n")

    if not tables:
        print("  No tables found — run export_retail_to_supabase.py first!")
        return {"embedded": 0, "skipped": 0}

    # -- warmup embed (validates API key) -------------------------------------
    print(f"  Using: {config.EMBEDDING_MODEL} @ {config.EMBEDDING_DIMENSIONS}-dim (MRL)\n")

    # -- process each table ---------------------------------------------------
    embedded = 0
    skipped  = 0
    t_start  = time.perf_counter()

    for table in tables:
        print(f"  [{table}]", end="")

        # Introspect
        columns = get_table_columns(cur, table)
        fks     = get_table_fks(cur, table)

        if not columns:
            print("  -> no columns found, skipping")
            continue

        # Hash
        new_hash    = compute_schema_hash(columns, fks)
        stored_hash = get_stored_hash(cur, table)

        if stored_hash == new_hash:
            print(f"  unchanged (hash={new_hash[:8]}...) -> SKIP")
            skipped += 1
            continue

        # Fetch sample rows for LLM description
        sample_rows = []
        try:
            cur.execute(f'SELECT * FROM "{table}" LIMIT 3')
            sample_rows = cur.fetchall()
        except Exception as err:
            print(f" (warning: could not fetch sample rows: {err})", end="")

        # Build description & embed
        description = None
        if config.GOOGLE_API_KEY:
            description = generate_llm_description(table, columns, sample_rows)
        if not description:
            description = build_description(table, columns, fks)
            
        vector = _embed(description)

        # UPSERT into table_embeddings
        cur.execute("""
            INSERT INTO table_embeddings (table_name, description, embedding, column_hash, updated_at)
            VALUES (%s, %s, %s::vector, %s, %s)
            ON CONFLICT (table_name) DO UPDATE SET
                description = EXCLUDED.description,
                embedding   = EXCLUDED.embedding,
                column_hash = EXCLUDED.column_hash,
                updated_at  = EXCLUDED.updated_at
        """, (
            table,
            description,
            str(vector),      # pgvector accepts '[0.1, 0.2, ...]' string
            new_hash,
            datetime.now(timezone.utc),
        ))
        conn.commit()

        action = "UPDATED" if stored_hash else "NEW"
        print(f"  {action} (hash={new_hash[:8]}...)")
        embedded += 1

    elapsed = time.perf_counter() - t_start
    cur.close()
    conn.close()

    print("\n" + "=" * 62)
    print(f"  Done!  Embedded: {embedded}  |  Skipped (unchanged): {skipped}")
    print(f"  Time: {elapsed:.1f}s")
    print("=" * 62)
    
    return {"embedded": embedded, "skipped": skipped}


if __name__ == "__main__":
    sync_embeddings()
