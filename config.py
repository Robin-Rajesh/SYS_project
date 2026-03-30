"""
config.py — Central Configuration for the Agentic Sales Data Analyst
=====================================================================
- Loads environment variables from a .env file via python-dotenv.
- Defines all project paths using pathlib.Path for cross-platform safety.
- Auto-creates required directories on import.
- Defines model and embedding settings.

CHANGE LOG:
  - DB_PATH now points to sales_normalized.db (normalised star schema).
    The old sales.db can remain in data/ and will still be ATTACHED
    automatically by the multi-database feature.
"""

import os
from pathlib import Path
from dotenv import load_dotenv

# ═══════════════════════════════════════════════════════════════
# 1. LOAD ENVIRONMENT VARIABLES
# ═══════════════════════════════════════════════════════════════

BASE_DIR = Path("C:/SEM5/SYS_project")   # ← update if your project root changes
load_dotenv(dotenv_path=BASE_DIR / ".env")

GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")

# ═══════════════════════════════════════════════════════════════
# 2. PROJECT PATHS
# ═══════════════════════════════════════════════════════════════

DATA_DIR        = BASE_DIR / "data"
DOCS_DIR        = BASE_DIR / "docs"
VECTOR_STORE_DIR = BASE_DIR / "vector_store"
OUTPUTS_DIR     = BASE_DIR / "outputs"

# ─── DEFAULT DATABASE ──────────────────────────────────────────
import urllib.parse

# 1. Try to load Supabase Cloud DB from environment
supabase_url = os.getenv("SUPABASE_DB_URL", "").strip()

if supabase_url and "supabase.co" in supabase_url:
    IS_CLOUD = True
    # Parse to safely URL encode password
    prefix = supabase_url.split("://")[0] + "://"
    rest = supabase_url.split("://")[1]
    
    user_pass = rest.split("@")[0]
    host_db = rest.split("@")[1]
    
    user = user_pass.split(":")[0]
    password = user_pass.split(":")[1]
    
    if password.startswith("[") and password.endswith("]"):
        password = password[1:-1]
        
    encoded_password = urllib.parse.quote_plus(password)
    DB_URI = f"{prefix}{user}:{encoded_password}@{host_db}"
    # Supabase forces 5432 to be IPv6 only, which hangs on local machines. Auto-switch to 6543 (IPv4 pooler).
    if "supabase.co:5432" in DB_URI:
        DB_URI = DB_URI.replace("supabase.co:5432", "supabase.co:6543")
        
    # Dummy path for backward compatibility in the app
    DB_PATH = DATA_DIR / "cloud_postgres.db" 
else:
    IS_CLOUD = False
    DB_PATH = DATA_DIR / "sales_normalized_1_1.db"
    DB_URI = f"sqlite:///{DB_PATH}"

# ═══════════════════════════════════════════════════════════════
# 3. MODEL & EMBEDDING SETTINGS
# ═══════════════════════════════════════════════════════════════

MODEL_NAME      = "gemini-2.5-flash"      # Google Gemini model ID
EMBEDDING_MODEL = "all-MiniLM-L6-v2"      # HuggingFace sentence-transformers (local, free)
MAX_RETRIES     = 3                        # Max SQL self-correction attempts

# ═══════════════════════════════════════════════════════════════
# 3.1 EMAIL SETTINGS
# ═══════════════════════════════════════════════════════════════

SMTP_SERVER      = os.getenv("SMTP_SERVER",      "smtp.gmail.com")
SMTP_PORT        = int(os.getenv("SMTP_PORT",    "587") or "587")
SENDER_EMAIL     = os.getenv("SENDER_EMAIL",     "")
SENDER_PASSWORD  = os.getenv("SENDER_PASSWORD",  "")
RECIPIENT_EMAIL  = os.getenv("RECIPIENT_EMAIL",  "")

# ═══════════════════════════════════════════════════════════════
# 4. AUTO-CREATE DIRECTORIES
# ═══════════════════════════════════════════════════════════════

for directory in [DATA_DIR, DOCS_DIR, VECTOR_STORE_DIR, OUTPUTS_DIR]:
    directory.mkdir(parents=True, exist_ok=True)

# ═══════════════════════════════════════════════════════════════
# 5. GENERATE .env.example (idempotent — safe to re-run)
# ═══════════════════════════════════════════════════════════════

_env_example_path = BASE_DIR / ".env.example"
_env_example_content = """\
# ═══════════════════════════════════════════════════════════════
# Agentic Sales Data Analyst — Environment Variables
# ═══════════════════════════════════════════════════════════════
# 1. Get a free API key at https://aistudio.google.com/app/apikey
# 2. Copy this file:  copy .env.example .env
# 3. Replace the placeholder with your actual key.
# ═══════════════════════════════════════════════════════════════

GOOGLE_API_KEY=your_key_here

# Optional — only needed if you use the email report feature
SMTP_SERVER=smtp.gmail.com
SMTP_PORT=587
SENDER_EMAIL=you@gmail.com
SENDER_PASSWORD=your_app_password
RECIPIENT_EMAIL=manager@company.com
"""

with open(_env_example_path, "w", encoding="utf-8") as f:
    f.write(_env_example_content)