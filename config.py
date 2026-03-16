"""
config.py — Central Configuration for the Agentic Sales Data Analyst
=====================================================================
- Loads the Google API key from a .env file using python-dotenv.
- Defines all project paths using pathlib.Path for cross-platform safety.
- Auto-creates required directories on import.
- Defines model and embedding settings.
"""

import os
from pathlib import Path
from dotenv import load_dotenv

# ═══════════════════════════════════════════════════════════════
# 1. LOAD ENVIRONMENT VARIABLES
# ═══════════════════════════════════════════════════════════════
# load_dotenv() reads the .env file located in the project root
# and injects the variables into os.environ so they are accessible
# via os.getenv() throughout the application.

BASE_DIR = Path("C:/SEM5/SYS_project")         # Project root directory
load_dotenv(dotenv_path=BASE_DIR / ".env")      # Load API key from .env

GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")    # Gemini API key

# ═══════════════════════════════════════════════════════════════
# 2. PROJECT PATHS (all using pathlib.Path for Windows safety)
# ═══════════════════════════════════════════════════════════════
# pathlib.Path handles forward/back-slash conversion automatically,
# which prevents common Windows path errors.

DATA_DIR = BASE_DIR / "data"                    # SQLite DB + generator
DOCS_DIR = BASE_DIR / "docs"                    # Policy / catalog docs
VECTOR_STORE_DIR = BASE_DIR / "vector_store"    # ChromaDB persistence
OUTPUTS_DIR = BASE_DIR / "outputs"              # Chart PNG / HTML output
DB_PATH = DATA_DIR / "sales.db"                 # SQLite database file

# ═══════════════════════════════════════════════════════════════
# 3. MODEL & EMBEDDING SETTINGS
# ═══════════════════════════════════════════════════════════════

MODEL_NAME = "gemini-2.5-flash"                 # Google Gemini model ID
EMBEDDING_MODEL = "all-MiniLM-L6-v2"           # HuggingFace sentence-transformers model (local, free)
MAX_RETRIES = 3                                 # Max SQL self-correction attempts

# ═══════════════════════════════════════════════════════════════
# 4. AUTO-CREATE DIRECTORIES
# ═══════════════════════════════════════════════════════════════
# Create every required directory if it does not already exist.
# exist_ok=True means no error is raised if the directory is present.

for directory in [DATA_DIR, DOCS_DIR, VECTOR_STORE_DIR, OUTPUTS_DIR]:
    directory.mkdir(parents=True, exist_ok=True)

# ═══════════════════════════════════════════════════════════════
# 5. GENERATE .env.example (idempotent — safe to re-run)
# ═══════════════════════════════════════════════════════════════
# This creates a template .env.example so new users know exactly
# which environment variables are required.

_env_example_path = BASE_DIR / ".env.example"
_env_example_content = """\
# ═══════════════════════════════════════════════════════════════
# Agentic Sales Data Analyst — Environment Variables
# ═══════════════════════════════════════════════════════════════
# 1. Get a free API key at https://aistudio.google.com/app/apikey
# 2. Copy this file to .env:   copy .env.example .env
# 3. Replace the placeholder below with your actual key.
# ═══════════════════════════════════════════════════════════════
GOOGLE_API_KEY=your_key_here
"""

# Write .env.example every time config.py is imported, keeping it up-to-date
with open(_env_example_path, "w", encoding="utf-8") as f:
    f.write(_env_example_content)
