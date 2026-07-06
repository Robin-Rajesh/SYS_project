import psycopg2
import sys
from pathlib import Path
sys.path.append(str(Path(__file__).resolve().parent))
import config

def migrate():
    print("Connecting to DB...")
    try:
        conn = psycopg2.connect(**config.NEW_SUPABASE_DB_PARAMS)
        conn.autocommit = True
        cur = conn.cursor()
        
        print("Running migration...")
        cur.execute("ALTER TABLE table_embeddings DROP COLUMN IF EXISTS embedding;")
        cur.execute("ALTER TABLE table_embeddings ADD COLUMN embedding VECTOR(1536);")
        cur.execute("DROP INDEX IF EXISTS idx_table_embeddings_hnsw;")
        cur.execute("CREATE INDEX idx_table_embeddings_hnsw ON table_embeddings USING hnsw (embedding vector_cosine_ops);")
        
        try:
            cur.execute("TRUNCATE TABLE langchain_pg_embedding;")
            print("Truncated langchain_pg_embedding.")
        except Exception as e:
            print(f"Notice: Could not truncate langchain_pg_embedding (may not exist yet): {e}")
        
        cur.close()
        conn.close()
        print("Migration complete.")
    except Exception as e:
        print(f"Error during migration: {e}")

if __name__ == "__main__":
    migrate()
