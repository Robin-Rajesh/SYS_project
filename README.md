# 📊 Enterprise AI Data Analytics Portal

A production-ready, cloud-integrated analytical platform that transforms natural language questions into professional data insights, interactive charts, and executive reports.

---

## 🚀 Overview

This application is an **Agentic Data Analyst** built to bridge the gap between complex databases and business stakeholders. Leveraging the **Google Gemini Pro** LLM and a hardened **PostgreSQL** cloud infrastructure, it allows users to chat with their data, visualize trends, and perform AI-driven quality audits without writing a single line of SQL.

---

## 🛠️ Technology Stack

### **Backend (The "Brain")**
- **Core**: [FastAPI](https://fastapi.tiangolo.com/) (High-performance Python API)
- **AI Orchestration**: [LangChain](https://www.langchain.com/) & [Google Gemini Pro](https://deepmind.google/technologies/gemini/)
- **Database**: [Supabase PostgreSQL](https://supabase.com/database) with **SQLAlchemy** ORM
- **Connectivity**: **Session Pooling** (Port 6543) for resilient cloud networking
- **RAG (Retrieval Augmented Generation)**: [pgvector](https://supabase.com/docs/guides/database/extensions/pgvector) on Supabase for searching internal policy documents

### **Frontend (The "Face")**
- **Framework**: [React](https://react.dev/) (v19)
- **Visuals**: [Plotly.js](https://plotly.com/javascript/) & [Lucide-React](https://lucide.dev/) icons
- **Styling**: Premium "Glassmorphism" Dark Mode (Vanilla CSS)
- **Robustness**: Custom `safeFetch` error-handling layer to prevent runtime crashes during server reloads

---

## ✨ Key Features

### 1. **Conversational AI Assistant**
- Ask questions in plain English (*"Which regions performed best in Q3?"*).
- Real-time streaming responses with "Thought Traces" (view the AI's internal reasoning).
- Star Schema awareness — the AI understands your table relationships before querying.

### 2. **Analytical Data Explorer**
- High-performance data grids with sorting, filtering, and global table search.
- **AI Data Quality Scan**: Instant audits to find anomalies or business logic violations.

### 3. **Relationship Viewer (Star Schema)**
- Interactive visualization of your database structure.
- Auto-mapped JOIN logic that allows the AI to combine data from multiple tables seamlessly.

### 4. **Executive Reporting Hub**
- Generate professional HTML reports with embedded charts.
- Automated Daily Scheduler: Configure the AI to email performance summaries to stakeholders every morning.

### 5. **AI Policy Hub**
- Upload `.txt` manuals or product catalogs.
- Semantic Research: Ask the AI questions about your company's internal documentation.

---

## 🗄️ Database & Vector Storage Architecture

### **1. Relational Cloud Database (Supabase PostgreSQL)**
The core analytical engine runs on **Supabase**. We transitioned from local SQLite databases to a robust, cloud-hosted PostgreSQL environment to support enterprise-level scaling. 
- **Migration**: The `scripts/migrate_to_supabase.py` tool automates the secure transfer of local data directly into Supabase.
- **Connection Pooling**: We utilize Supabase's transaction pooler (Port 6543) to maintain stable, persistent connections and avoid timeouts during heavy AI query generations.
- **Role**: It stores all transactional sales data, customer records, and employee structures, forming the basis of the "Star Schema" queried by the AI via `sql_tool.py`.

### **2. Semantic Vector Store (pgvector on Supabase)**
To make the AI aware of unstructured corporate data (rules, policies, guidelines), we use **pgvector** — a PostgreSQL extension that adds vector similarity search natively to Supabase.
- **Embedding Generation**: Text from the `docs/` folder (e.g., employee handbooks, sales policies) is split into chunks and converted into dense vector embeddings.
- **RAG Integration**: Powered by `tools/rag_tool.py`, pgvector allows the AI to perform similarity searches to instantly retrieve relevant policy context before answering a user's question.
- **Single Service**: Vector embeddings are stored directly in Supabase, alongside relational data — no separate ChromaDB service or persistent volume needed.

### **3. Schema Relationships Table**
The FK (Foreign Key) relationships between tables are synced from `data/schema_metadata.json` into a `schema_relationships` table on Supabase at startup via `scripts/sync_schema.py`. This enables:
- **Multi-instance resilience**: All app instances read from the same source of truth.
- **Fast runtime traversal**: Each instance loads the table once into a Python dict for 1-hop FK expansion.

---

## 🛡️ Stability & Hardening

The system is architected for **Enterprise Reliability**:
- **Connection Pre-Ping**: Validates database health before every query.
- **Auto-Recycling**: Refreshes idle cloud connections every 120 seconds.
- **Frontend Crash-Proofing**: The React app is resilient to momentary backend restarts.

---

## 🚦 Getting Started

### **1. Backend Setup**
```bash
# Install dependencies
pip install -r requirements.txt

# Configure environment
cp .env.example .env
# Add your GOOGLE_API_KEY, SUPABASE_DB_URL, and SMTP settings (for reports)

# Seed and migrate your database (If setting up for the first time)
python scripts/generate_master_data.py
python scripts/migrate_to_supabase.py
python scripts/create_users_db.py

# Sync schema relationships to Supabase (run once, or after schema changes)
python scripts/sync_schema.py

# Start the API
uvicorn api:app --reload --port 8000
```

### **2. Interactive Terminal Agent (Optional)**
```bash
# Run the conversational AI interface directly from the terminal
python main.py
```

### **3. Frontend Setup**
```bash
cd frontend
npm install
npm start
```

---

## 📂 Project Structure
- `api.py`: Main FastAPI server and routing.
- `main.py` / `app.py`: Interactive terminal chat interface and CLI tools.
- `agent.py`: LangChain orchestration and core AI logic.
- `config.py`: Hardened database engine and environment management.
- `tools/`: Specialized AI tools (`sql_tool.py`, `rag_tool.py`, `visualizer_tool.py`).
- `scripts/`: Initialization scripts (`generate_master_data.py`, `migrate_to_supabase.py`, `create_users_db.py`) and automated reporting (`cron_report_sender.py`).
- `docs/`: Policy documents and corporate handbooks for RAG queries.
- `frontend/src/App.js`: Monolithic, high-performance React entry point.
- `data/schema_metadata.json`: The "Mental Map" of your database.

---

*Built with ❤️ for Robin-Rajesh/SYS_project*
