"""
schema_retriever.py — Semantic Table Schema Retrieval and FK Expansion
=======================================================================
Finds the most relevant tables for any user query using:
  1. pgvector similarity search on Supabase (using Google gemini-embedding-001 MRL @ 1536-dim).
  2. 1-hop Star Schema expansion via schema_relationships table.
  3. Configurable cosine similarity threshold pruning (PRUNING_THRESHOLD).
"""

import os
from collections import defaultdict
import psycopg2
import google.genai as genai
import config
from tools.sql_tool import get_engine

# Initialize the new google.genai client (replaces deprecated google.generativeai)
_genai_client = genai.Client(api_key=config.GOOGLE_API_KEY)

def _embed_query(text: str) -> list[float]:
    """Embed a query string using gemini-embedding-001 with MRL at configured dims."""
    result = _genai_client.models.embed_content(
        model=config.EMBEDDING_MODEL,
        contents=text,
        config={"output_dimensionality": config.EMBEDDING_DIMENSIONS},
    )
    return result.embeddings[0].values

def retrieve_resolved_tables(query: str) -> list[str]:
    """
    Given a user natural language query, performs similarity search, 
    1-hop expansion, and threshold-based pruning to return a list of 
    resolved table names to include in the agent prompt.
    """
    # 1. Fallback to including all tables if we are not in cloud mode or if any error occurs
    if not config.IS_CLOUD:
        try:
            from sqlalchemy import inspect
            inspector = inspect(get_engine())
            return inspector.get_table_names()
        except Exception:
            return []

    try:
        # Load configurable pruning threshold (default: 0.30)
        prun_threshold = float(os.getenv("PRUNING_THRESHOLD", "0.30"))
        
        # 2. Embed user question
        query_vec = _embed_query(query)
        
        # Connect to Supabase
        conn = psycopg2.connect(**config.NEW_SUPABASE_DB_PARAMS)
        cur = conn.cursor()
        
        # 3. Retrieve ALL business tables with similarity scores
        # Exclude internal/system tables that should never appear in business queries
        EXCLUDED_TABLES = ('langchain_pg_collection', 'langchain_pg_embedding', 'sample', 'table_embeddings')
        cur.execute("""
            SELECT table_name, 1 - (embedding <=> %s::vector) AS similarity
            FROM table_embeddings
            WHERE table_name NOT IN %s
            ORDER BY similarity DESC
        """, (str(query_vec), EXCLUDED_TABLES))
        
        rows = cur.fetchall()
        if not rows:
            cur.close()
            conn.close()
            return []
            
        # Parse and filter results using a DYNAMIC RELATIVE threshold
        # We find the top score, and keep all tables within 0.16 of that top score.
        # This prevents absolute threshold failures caused by asymmetrical document lengths.
        max_sim = float(rows[0][1])
        table_similarities = {}
        top_k = []
        
        # ABSOLUTE FLOOR GUARD: if best match scores below 0.15, the query is truly
        # random noise with no meaningful signal. Return only the single best match.
        ABSOLUTE_FLOOR = 0.15
        if max_sim < ABSOLUTE_FLOOR:
            best_name = rows[0][0]
            table_similarities = {r[0]: float(r[1]) for r in rows}
            cur.close()
            conn.close()
            return [best_name]
        
        for r in rows:
            name = r[0]
            sim = float(r[1])
            table_similarities[name] = sim
            if sim >= (max_sim - 0.16):
                top_k.append(name)
            
        resolved_set = set(top_k)
        
        # 4. SELECTIVE 1-hop FK expansion
        # We do NOT blindly expand to all FK neighbors (that killed precision).
        # We do NOT skip expansion entirely (that dropped order_items and bridge tables).
        # Instead: only expand to an FK neighbor if it scored >= FK_FLOOR_THRESHOLD
        # in the original vector search. If a table has some semantic relevance to the
        # query AND is connected to an already-selected table, include it.
        FK_FLOOR_THRESHOLD = 0.20
        
        cur.execute("SELECT from_table, to_table FROM schema_relationships")
        fk_rows = cur.fetchall()
        adj = defaultdict(set)
        for from_t, to_t in fk_rows:
            adj[from_t].add(to_t)
            adj[to_t].add(from_t)
            
        for t in list(top_k):
            for neighbor in adj[t]:
                if neighbor not in resolved_set:
                    neighbor_score = table_similarities.get(neighbor, 0.0)
                    if neighbor_score >= FK_FLOOR_THRESHOLD:
                        resolved_set.add(neighbor)
                
        cur.close()
        conn.close()
        
        # Hard cap: never return more than 8 tables regardless of threshold outcomes.
        # Prevents catastrophic prompt flooding on broad or ambiguous queries.
        MAX_TABLES = 8
        result = sorted(list(resolved_set))
        if len(result) > MAX_TABLES:
            # Prioritize tables in top_k (directly matched), then FK-expanded ones
            top_k_set = set(top_k)
            prioritized = [t for t in result if t in top_k_set]
            expanded = [t for t in result if t not in top_k_set]
            result = (prioritized + expanded)[:MAX_TABLES]
        
        return result

        
    except Exception as exc:
        print(f"[Schema Retriever] Error during semantic schema search: {exc}")
        # Graceful fallback: return all tables
        try:
            from sqlalchemy import inspect
            inspector = inspect(get_engine())
            return inspector.get_table_names()
        except Exception:
            return []

def get_resolved_schema_context(query: str) -> str:
    """
    Returns a core schema block text of the resolved tables.
    """
    if not query:
        # If no query is provided (e.g. startup/inspect), return all tables or first 10
        try:
            from sqlalchemy import inspect
            inspector = inspect(get_engine())
            tables = inspector.get_table_names()[:10]
        except Exception:
            tables = []
    else:
        tables = retrieve_resolved_tables(query)
        
    if not tables:
        return "No schema metadata found or active database connection unavailable."
        
    lines = ["--- RESOLVED DATABASE TABLES FOR THIS QUERY ---"]
    engine = get_engine()
    
    # We can inspect the tables using the standard inspector
    from sqlalchemy import inspect
    inspector = inspect(engine)
    
    for table_name in tables:
        try:
            columns = inspector.get_columns(table_name)
            pk = inspector.get_pk_constraint(table_name)
            fks = inspector.get_foreign_keys(table_name)
            
            lines.append(f"CREATE TABLE {table_name} (")
            col_lines = []
            
            # Add columns
            for col in columns:
                col_lines.append(f"    {col['name']} {col['type']}")
                
            # Add primary key if it exists
            if pk and pk.get('constrained_columns'):
                pk_cols = ", ".join(pk['constrained_columns'])
                col_lines.append(f"    PRIMARY KEY ({pk_cols})")
                
            # Add foreign keys if they exist
            for fk in fks:
                fk_cols = ", ".join(fk['constrained_columns'])
                ref_table = fk['referred_table']
                ref_cols = ", ".join(fk['referred_columns'])
                col_lines.append(f"    FOREIGN KEY ({fk_cols}) REFERENCES {ref_table}({ref_cols})")
            
            lines.append(",\n".join(col_lines))
            lines.append(");\n")
        except Exception:
            pass
            
    return "\n".join(lines)
