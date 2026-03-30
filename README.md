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
- **RAG (Retrieval Augmented Generation)**: [ChromaDB](https://www.trychroma.com/) for searching internal policy documents

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
# Add your GOOGLE_API_KEY and SUPABASE_DB_URL

# Start the API
uvicorn api:app --reload --port 8000
```

### **2. Frontend Setup**
```bash
cd frontend
npm install
npm start
```

---

## 📂 Project Structure
- `api.py`: Main FastAPI server and routing.
- `agent.py`: LangChain orchestration and tool definitions.
- `config.py`: Hardened database engine and environment management.
- `tools/`: Specialized AI tools (SQL, Hybrid Search, Visualizer).
- `frontend/src/App.js`: Monolithic, high-performance React entry point.
- `data/schema_metadata.json`: The "Mental Map" of your database.

---

*Built with ❤️ for Robin-Rajesh/SYS_project*
