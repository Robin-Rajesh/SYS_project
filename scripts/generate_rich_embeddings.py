import sys
import os
import psycopg2
import pandas as pd
from sqlalchemy import create_engine, inspect, text
import google.genai as genai

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
import config

# Initialize the new google.genai client (replaces deprecated google.generativeai)
_genai_client = genai.Client(api_key=config.GOOGLE_API_KEY)

def generate_table_metadata(engine, table_name):
    """
    Analyzes a table and returns a PII-safe metadata string containing:
    - Column names and types
    - Numeric ranges (min/max)
    - Date ranges (min/max)
    - Categorical distinct values (for low cardinality text columns)
    """
    insp = inspect(engine)
    columns = insp.get_columns(table_name)
    
    col_names = [c['name'] for c in columns]
    col_types = [str(c['type']) for c in columns]
    
    numeric_summary = []
    date_summary = []
    enum_summary = []
    
    with engine.connect() as conn:
        for c in columns:
            col = c['name']
            ctype = str(c['type']).upper()
            
            try:
                if 'INT' in ctype or 'NUMERIC' in ctype or 'FLOAT' in ctype or 'DECIMAL' in ctype:
                    res = conn.execute(text(f'SELECT MIN("{col}"), MAX("{col}") FROM "{table_name}"')).fetchone()
                    if res and res[0] is not None:
                        numeric_summary.append(f"{col}: {res[0]} to {res[1]}")
                        
                elif 'DATE' in ctype or 'TIME' in ctype:
                    res = conn.execute(text(f'SELECT MIN("{col}"), MAX("{col}") FROM "{table_name}"')).fetchone()
                    if res and res[0] is not None:
                        date_summary.append(f"{col}: {res[0]} to {res[1]}")
                        
                elif 'VARCHAR' in ctype or 'TEXT' in ctype or 'CHAR' in ctype:
                    # Check cardinality
                    count_res = conn.execute(text(f'SELECT COUNT(DISTINCT "{col}") FROM "{table_name}"')).fetchone()
                    if count_res and count_res[0] is not None and count_res[0] <= 15:
                        # Low cardinality - get distinct values
                        distinct_res = conn.execute(text(f'SELECT DISTINCT "{col}" FROM "{table_name}" WHERE "{col}" IS NOT NULL')).fetchall()
                        vals = [str(r[0]) for r in distinct_res]
                        if vals:
                            enum_summary.append(f"{col}: {', '.join(vals)}")
            except Exception as e:
                # Some columns might cause issues (e.g. geometric types), skip gracefully
                print(f"Warning: Could not analyze column {col} in table {table_name}: {e}")

    desc = f"Columns: {', '.join(col_names)}\n"
    if numeric_summary:
        desc += f"Numeric ranges: {'; '.join(numeric_summary)}\n"
    if date_summary:
        desc += f"Date ranges: {'; '.join(date_summary)}\n"
    if enum_summary:
        desc += f"Categorical Enums: {'; '.join(enum_summary)}\n"
        
    return desc

def _embed(text: str) -> list[float]:
    """Embed text using gemini-embedding-001 with MRL at configured dimensions."""
    result = _genai_client.models.embed_content(
        model=config.EMBEDDING_MODEL,
        contents=text,
        config={"output_dimensionality": config.EMBEDDING_DIMENSIONS},
    )
    return result.embeddings[0].values

def run():
    print("Connecting to database...")
    engine = create_engine(config.DB_URI)
    insp = inspect(engine)
    
    tables = insp.get_table_names()
    print(f"Found {len(tables)} tables. Generating rich embeddings with gemini-embedding-001 @ {config.EMBEDDING_DIMENSIONS}-dim...")
    
    # We will exclude internal/schema tables
    exclude = ['schema_relationships', 'table_embeddings', 'alembic_version']
    tables_to_embed = [t for t in tables if t not in exclude]
    
    conn = psycopg2.connect(**config.NEW_SUPABASE_DB_PARAMS)
    cur = conn.cursor()
    
    # Create the table if it doesn't exist
    cur.execute(f"""
        CREATE EXTENSION IF NOT EXISTS vector;
        CREATE TABLE IF NOT EXISTS table_embeddings (
            id SERIAL PRIMARY KEY,
            table_name TEXT UNIQUE,
            description TEXT,
            embedding vector({config.EMBEDDING_DIMENSIONS})
        );
    """)
    conn.commit()
    
    # Hardcoded business intent to ensure semantic matching for abstract concepts
    BUSINESS_DESCRIPTIONS = {
        "shipments": "Tracks delivery status of each order. Used for fulfillment and logistics analysis.",
        "stores": "Stores each retail store location and city. Used for regional, territory, area, geographic, location, and market analysis. Linked to orders and employees.",
        "suppliers": "Stores supplier/vendor data. Linked to products for supply chain, vendor, and sourcing analysis.",
        "order_items": "Line items for every order. Used to calculate revenue, sales, quantity, and profit margins.",
        "orders": "Tracks every purchase event. Links customers to stores and promotions. Used for timeline and trend analysis.",
        "customers": "Customer demographic data. Used for churn, retention, and demographic analysis.",
        "products": "Inventory and product catalog. Used for brand, category, and pricing analysis.",
        "categories": "Product categories (e.g. Toys, Electronics).",
        "employees": "Staff and HR data including salaries. Used for manager, sales rep, employee, staff performance, HR, headcount, and compensation analysis. Linked to stores.",
        "promotions": "Discount codes and marketing campaigns. Used for marketing ROI and sales events.",
        "returns": "Refunds and returned damaged items. Used for quality control and return rate analysis. CRITICAL: A return row corresponds to an order_item. To find the total quantity of items returned, you MUST join with order_items and use SUM(qty), do NOT use COUNT(return_id).",
        "payments": "Financial transactions for orders. Used for payment method and credit card failure analysis."
    }
    
    for table in tables_to_embed:
        print(f"Processing table: {table}")
        
        base_desc = BUSINESS_DESCRIPTIONS.get(table, f"The {table} table.")
            
        # 1. Generate Metadata String
        meta_description = generate_table_metadata(engine, table)
        
        final_description = f"Table: {table}\nBusiness Purpose: {base_desc}\n{meta_description}"
        print(final_description)
        
        # 2. Vectorize using Gemini Embedding API (MRL @ configured dims)
        vector = _embed(final_description)
        
        # 3. Upsert into Supabase
        cur.execute("""
            INSERT INTO table_embeddings (table_name, description, embedding)
            VALUES (%s, %s, %s::vector)
            ON CONFLICT (table_name) DO UPDATE 
            SET description = EXCLUDED.description,
                embedding = EXCLUDED.embedding;
        """, (table, final_description, str(vector)))
        
        print(f"-> Updated Supabase for {table}\n")
        
    conn.commit()
    cur.close()
    conn.close()
    print("Done! Rich embeddings have been successfully generated and saved to Supabase.")

if __name__ == "__main__":
    run()
