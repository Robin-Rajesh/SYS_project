import os
import urllib.parse
from sqlalchemy import create_engine, inspect
import pandas as pd
from dotenv import load_dotenv

load_dotenv()

# 1. Source SQLite Database
source_url = "sqlite:///C:/SEM5/SYS_project/data/sales_normalized_1_1.db"

# 2. Target Supabase Database
# Read directly from .env
db_url_env = os.getenv("SUPABASE_DB_URL", "").strip()

# Supabase gives: postgresql://postgres:[YOUR-PASSWORD]@db.xxx.supabase.co:5432/postgres
# We need to extract the password, strip the brackets if they exist, URL encode it, and rebuild the URL
if "@" in db_url_env and "//" in db_url_env:
    # Basic parsing to fix common copy-paste errors
    prefix = db_url_env.split("://")[0] + "://" # postgresql://
    rest = db_url_env.split("://")[1]
    
    user_pass = rest.split("@")[0]
    host_db = rest.split("@")[1]
    
    user = user_pass.split(":")[0]
    password = user_pass.split(":")[1]
    
    # Strip brackets if user left them in from [YOUR-PASSWORD]
    if password.startswith("[") and password.endswith("]"):
        password = password[1:-1]
        
    # URL encode special characters
    encoded_password = urllib.parse.quote_plus(password)
    
    dest_url = f"{prefix}{user}:{encoded_password}@{host_db}"
    if "supabase.co:5432" in dest_url:
        dest_url = dest_url.replace("supabase.co:5432", "supabase.co:6543")
else:
    print("Invalid SUPABASE_DB_URL in .env")
    exit(1)

print(f"🔥 Connecting to local SQLite database...")
sqlite_engine = create_engine(source_url)
print(f"☁️ Connecting to Supabase PostgreSQL database...")
pg_engine = create_engine(dest_url)

inspector = inspect(sqlite_engine)
tables = inspector.get_table_names()

print(f"📦 Found {len(tables)} tables to migrate.")

for table in tables:
    print(f"   -> Migrating table '{table}'...")
    try:
        df = pd.read_sql(f"SELECT * FROM {table}", sqlite_engine)
        df.to_sql(table, pg_engine, if_exists="replace", index=False)
        print(f"      ✅ Success: {len(df)} rows migrated.")
    except Exception as e:
        print(f"      ❌ Failed: {str(e)}")

print("\n🎉 Migration to Supabase Complete!")
