import asyncio
from sqlalchemy import create_engine, text
from config import NEW_SUPABASE_DB_URI

def check_db():
    if not NEW_SUPABASE_DB_URI:
        print("No NEW_SUPABASE_DB_URI found.")
        return

    engine = create_engine(NEW_SUPABASE_DB_URI)
    with engine.connect() as conn:
        # Check pgvector extension
        res = conn.execute(text("SELECT extname FROM pg_extension WHERE extname = 'vector'")).fetchall()
        print(f"pgvector extension: {'Installed' if res else 'Not Installed'}")

        # Check tables
        tables = conn.execute(text("SELECT tablename FROM pg_tables WHERE schemaname = 'public'")).fetchall()
        table_names = [t[0] for t in tables]
        
        print(f"table_embeddings exists: {'table_embeddings' in table_names}")
        print(f"schema_relationships exists: {'schema_relationships' in table_names}")

if __name__ == "__main__":
    check_db()
