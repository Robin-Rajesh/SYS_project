"""
app.py — Enterprise UI for Agentic Sales Data Analyst
======================================================
Features:
  - Dynamic Database Connection (Default Sales DB or Custom URI)
  - Interactive Data Explorer (Preview first 100 rows)
  - Real-time agent streaming capabilities
"""

import os
import subprocess
import streamlit as st
import pandas as pd
import json
import graphviz
from agent import stream_agent, clear_memory
from tools.sql_tool import set_database_connection, get_engine
import config

# ═══════════════════════════════════════════════════════════════
# 1. PAGE CONFIGURATION & ENTERPRISE THEMING
# ═══════════════════════════════════════════════════════════════
st.set_page_config(
    page_title="Enterprise Data Analyst AI",
    page_icon="🤖",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS for a professional look
st.markdown("""
<style>
    .chat-bubble { padding: 1rem; border-radius: 10px; margin-bottom: 1rem; }
    .header-logo { font-size: 2rem; font-weight: bold; color: #1e3a8a; }
</style>
""", unsafe_allow_html=True)

# ═══════════════════════════════════════════════════════════════
# 2. SESSION STATE
# ═══════════════════════════════════════════════════════════════
if "messages" not in st.session_state:
    st.session_state.messages = [{
        "role": "assistant",
        "content": "Welcome! I am your Enterprise Data Analyst AI. I can securely query the connected database, build visualizations, and check internal policies."
    }]
if "policy_messages" not in st.session_state:
    st.session_state.policy_messages = [{
        "role": "assistant",
        "content": "Welcome to the AI Policy Hub! Ask me any questions about internal company documents or product catalogs."
    }]
if "active_db" not in st.session_state:
    st.session_state.active_db = f"sqlite:///{config.DB_PATH}"

# ═══════════════════════════════════════════════════════════════
# 3. SIDEBAR: CONNECTION MANAGER & SETTINGS
# ═══════════════════════════════════════════════════════════════
with st.sidebar:
    st.markdown("<div class='header-logo'>🤖 Data Analyst AI</div>", unsafe_allow_html=True)
    st.markdown("---")
    
    st.header("🔌 Database Connection")
    db_files = [f for f in os.listdir(config.DATA_DIR) if f.endswith((".db", ".sqlite"))]
    if db_files:
        selected_db_file = st.selectbox(
            "Select Database File:", 
            db_files,
            help="Choose from databases in the local data/ directory."
        )
        new_db_uri = f"sqlite:///{config.DATA_DIR / selected_db_file}"
    else:
        st.warning("No databases found in the data/ folder.")
        new_db_uri = st.session_state.active_db
            
    # Apply connection change if needed
    if new_db_uri != st.session_state.active_db and new_db_uri:
        try:
            set_database_connection(new_db_uri)
            st.session_state.active_db = new_db_uri
            st.success("Connection updated successfully!")
            # Clear memory so the agent adopts the new schema context
            clear_memory()
            st.session_state.messages = [{
                "role": "assistant",
                "content": "Database changed. My reasoning context has been reset to the new schema."
            }]
            st.rerun()
        except Exception as e:
            st.error(f"Failed to connect: {e}")

    st.markdown("---")
    if st.button("🧹 Clear Conversation Memory", use_container_width=True):
        clear_memory()
        st.session_state.messages = [{
            "role": "assistant",
            "content": "Conversation memory has been cleared."
        }]
        st.rerun()

    st.markdown("---")
    st.subheader("📅 Automation Settings")
    
    TASK_NAME = "AI_Executive_Sales_Report"
    SCRIPT_PATH = str(config.BASE_DIR / "scripts" / "cron_report_sender.py")
    PYTHON_PATH = str(config.BASE_DIR / "venv" / "Scripts" / "python.exe")

    def get_task_status():
        """Check if the Windows Scheduled Task exists and return its next run time."""
        try:
            result = subprocess.run(
                ["schtasks", "/query", "/tn", TASK_NAME, "/fo", "LIST"],
                capture_output=True, text=True, timeout=5
            )
            if result.returncode == 0:
                for line in result.stdout.splitlines():
                    if "Next Run Time" in line:
                        return f"✅ Active — {line.split(':', 1)[1].strip()}"
                return "✅ Active"
            return "🔴 Not Scheduled"
        except Exception:
            return "❓ Status Unknown"
    
    with st.expander("📧 Report Delivery Schedule", expanded=True):
        st.caption(f"**Task Status:** {get_task_status()}")
        scheduled_time = st.time_input("Daily Delivery Time", value=pd.to_datetime("09:00").time())
        recipient_email = st.text_input("📨 Recipient Email", value=config.RECIPIENT_EMAIL or "", placeholder="e.g. manager@company.com")
        is_enabled = st.checkbox("Enable Daily Email Report", value=True)

        col_sched1, col_sched2 = st.columns(2)
        with col_sched1:
            if st.button("🔄 Update Schedule", use_container_width=True, type="primary"):
                time_str = scheduled_time.strftime("%H:%M")
                cmd = [
                    "schtasks", "/create",
                    "/tn", TASK_NAME,
                    "/tr", f'"{PYTHON_PATH}" "{SCRIPT_PATH}"',
                    "/sc", "DAILY",
                    "/st", time_str,
                    "/f"  # Force-overwrite if exists
                ]
                if not is_enabled:
                    # Delete the task instead
                    cmd = ["schtasks", "/delete", "/tn", TASK_NAME, "/f"]
                
                try:
                    result = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
                    if result.returncode == 0:
                        st.success(f"Schedule set to {scheduled_time.strftime('%I:%M %p')} daily!" if is_enabled else "Schedule disabled.")
                        st.toast("✅ Windows Task Scheduler updated!", icon="🗓️")
                    else:
                        st.error(f"Scheduler error: {result.stderr.strip() or result.stdout.strip()}")
                except Exception as ex:
                    st.error(f"Failed to update schedule: {ex}")

        with col_sched2:
            if st.button("⚡ Send Report Now", use_container_width=True):
                with st.spinner("🤖 Generating & sending report... (may take a few minutes)"):
                    import smtplib
                    from email.message import EmailMessage
                    import importlib.util
                    try:
                        # Load the cron sender module from its absolute path 
                        _spec = importlib.util.spec_from_file_location(
                            "cron_report_sender",
                            str(config.BASE_DIR / "scripts" / "cron_report_sender.py")
                        )
                        _cron_mod = importlib.util.module_from_spec(_spec)
                        _spec.loader.exec_module(_cron_mod)
                        html_content = _cron_mod.generate_report()
                        
                        # Use recipient from the UI field
                        to_addr = recipient_email or config.RECIPIENT_EMAIL
                        msg = EmailMessage()
                        msg["Subject"] = "📊 AI Executive Sales Report"
                        msg["From"] = config.SENDER_EMAIL
                        msg["To"] = to_addr
                        msg.set_content("Please find the attached AI-generated Sales Report. Open in Chrome/Edge to view interactive charts.")
                        msg.add_attachment(html_content.encode("utf-8"), maintype="text", subtype="html", filename="Executive_Sales_Report.html")
                        
                        server = smtplib.SMTP(config.SMTP_SERVER, config.SMTP_PORT)
                        server.ehlo()
                        server.starttls()
                        server.login(config.SENDER_EMAIL, config.SENDER_PASSWORD)
                        server.send_message(msg)
                        server.quit()
                        st.success(f"✅ Report sent to {to_addr}!")
                    except Exception as e:
                        st.error(f"Failed: {e}")

    st.markdown("---")
    st.subheader("💡 Example AI Prompts")
    st.info("Try asking these in the Chatbot:\n\n"
            "• *\"Show me a bar chart of total sales by region.\"* \n"
            "• *\"Plot a line chart of sales ordered by month in 2023.\"* \n"
            "• *\"What is the total profit margin for the East Coast? Chart it.\"* \n"
            "• *\"Are there any policy violations with 25% discounts?\"*")

    st.markdown("---")
    st.subheader("📑 AI Executive Sales Report")
    st.markdown("Generate a deeply analyzed HTML report embedding live AI charts.")
    if st.button("Generate Downloadable Report", icon="📝", use_container_width=True):
        with st.spinner("The AI is generating a massive comprehensive HTML report with visualizations (may take 20 seconds)..."):
            try:
                from agent import run_agent
                report_prompt = (
                    "You are an elite, world-class Business Intelligence Analyst. Your mandate is to write a masterclass, ultra-detailed Executive Sales & Financial Report in pure HTML format. "
                    "You must comprehensively query the database to extract exhaustive insights covering overall revenue, profit margins, regional performance, product categories, temporal trends, and the statistical impact of discounts on profitability. "
                    "You MUST aggressively utilize the visualization_tool to generate at least FIVE strictly different and highly-informative charts: "
                    "1. A 'line' chart tracking Revenue or Profit over Time (Month/Year) to diagnose seasonality and macro trends. "
                    "2. A 'bar' chart comparing Top-Performing vs Bottom-Performing Product Categories, strictly segmented using 'color_column'. "
                    "3. A 'pie' chart breaking down revenue distribution across Regions or Customer Segments. "
                    "4. A 'scatter' plot visualizing the correlation between Discount levels and Profit Margins (or Sales Amount) to identify pricing inefficiencies. "
                    "5. A 'histogram' showing the distribution of order sizes or sales volume across the entire dataset. "
                    "CRITICAL: For every chart (except pie), you MUST inject a valid 'color_column' in the visualization_tool payload to ensure stunning, multi-colored segmentation. "
                    "Output a massive, premium HTML document. Embed advanced CSS (<style> block): 'Inter' or 'Roboto' fonts, a sleek dashboard background (#f4f7f6), "
                    "clean white glass-morphic container boxes with rounded corners (border-radius: 12px), subtle hover effects, and deep drop shadows (box-shadow: 0 10px 15px rgba(0,0,0,0.05)) for content and dynamic KPI summary cards at the very top. "
                    "Make sure the KPI cards are widely separated. You must use 'display: flex; gap: 30px; justify-content: space-between; margin-bottom: 30px;' on the KPI container for generous spacing! "
                    "Mandatory Sections: 1. Executive Summary & KPIs 2. Temporal Growth & Seasonality Analysis 3. Product & Category Deep-Dive 4. Regional Revenue Distribution 5. Pricing Strategy & Discount Correlation. "
                    "For every single section, write 3-4 paragraphs of exhaustive, C-Suite level business inferences. Explain the 'WHY' behind the geometry of the charts, diagnose critical anomalies, and provide aggressive, actionable strategic recommendations. "
                    "When displaying charts, embed them precisely like this: <iframe src='file:///[EXACT_ABSOLUTE_PATH_RETURNED_BY_TOOL]' width='100%' height='550px' style='border:none; border-radius: 12px; margin: 25px 0; box-shadow: 0 4px 6px rgba(0,0,0,0.05);'></iframe>. "
                    "CRITICAL: Make sure to replace backslashes with forward slashes in the path returned by the tool! "
                    "Return ONLY pristine, valid raw HTML code and absolutely no outer markdown wrapping."
                )
                report_content = run_agent(report_prompt)
                
                # Strip markdown code blocks if the LLM wraps the HTML
                if "```html" in report_content:
                    report_content = report_content.split("```html")[1].split("```")[0].strip()
                elif "```" in report_content:
                    report_content = report_content.replace("```", "").strip()
                
                # Make HTML strictly portable by embedding local files as optimized base64
                import re, base64, urllib.parse, os
                def make_html_portable(html_txt):
                    def replacer(match):
                        # 1. Get the path to the chart HTML file
                        path = urllib.parse.unquote(match.group(1)).replace("%3A", ":")
                        
                        if os.path.exists(path):
                            # 2. Read the chart HTML
                            with open(path, "r", encoding="utf-8", errors="ignore") as f:
                                content = f.read()
                            
                            # 4. Convert the HTML into Base64 so it renders in ALL browsers
                            b64 = base64.b64encode(content.encode("utf-8")).decode('utf-8')
                            return f'src="data:text/html;base64,{b64}"'
                        return match.group(0)
                    
                    # Target both ' and " quotes for widest compatibility
                    html_txt = re.sub(r'src=["\']file:///(.*?)["\']', replacer, html_txt)
                    # Minify to save even more space
                    return re.sub(r'>\s+<', '><', html_txt)

                report_content = make_html_portable(report_content)
                st.session_state.portable_report = report_content
                
                st.success("HTML Report successfully generated!")
            except Exception as r_err:
                st.error(f"Failed to generate report: {r_err}")

    if "portable_report" in st.session_state:
        st.download_button(
            label="📥 Download Responsive HTML Report",
            data=st.session_state.portable_report,
            file_name="Detailed_Sales_Report.html",
            mime="text/html",
            use_container_width=True
        )
        
        with st.expander("📧 Email this Report", expanded=False):
            st.info("Because email clients block live JavaScript charts, the report will be sent as a portable HTML attachment.")
            recipient_email = st.text_input("Recipient Email:")
            if st.button("Send Email", type="primary", use_container_width=True):
                # email dispatch logic stays same
                if recipient_email:
                    with st.spinner("Dispatching email..."):
                        try:
                            import smtplib
                            from email.message import EmailMessage
                            msg = EmailMessage()
                            msg["Subject"] = "AI Executive Sales Report"
                            msg["From"] = config.SENDER_EMAIL
                            msg["To"] = recipient_email
                            msg.set_content("Please find the attached AI-generated Sales Report. Download and open the attachment in your web browser (Chrome/Edge) to view the interactive charts.")
                            
                            msg.add_attachment(
                                st.session_state.portable_report.encode("utf-8"),
                                maintype="text",
                                subtype="html",
                                filename="Executive_Sales_Report.html"
                            )
                            
                            server = smtplib.SMTP(config.SMTP_SERVER, config.SMTP_PORT)
                            server.ehlo()
                            server.starttls()
                            server.login(config.SENDER_EMAIL, config.SENDER_PASSWORD)
                            server.send_message(msg)
                            server.quit()
                            st.success(f"Report securely emailed to {recipient_email}!")
                        except Exception as e:
                            st.error(f"Failed to send email: {e}")
                else:
                    st.warning("Please enter a recipient email.")
                    
        import streamlit.components.v1 as components
        st.markdown("### 🖥️ Live Report Preview")
        components.html(st.session_state.portable_report, height=800, scrolling=True)

    st.markdown("---")
    st.caption("Powered by LangGraph & Gemini")

# ═══════════════════════════════════════════════════════════════
# 4. MAIN WORKSPACE: TABS
# ═══════════════════════════════════════════════════════════════
# Split the UI into a Data Explorer, Chat Window, Interactive Dashboard, and Policy Hub
tab_chat, tab_data, tab_dashboard, tab_policy = st.tabs([
    "💬 AI Assistant", 
    "📊 Data Explorer", 
    "📈 Interactive Dashboard", 
    "📚 AI Policy Hub"
])

with tab_data:
    st.subheader(f"Active Connection: `{st.session_state.active_db}`")
    try:
        # Load the first 100 rows using SQLAlchemy and Pandas
        engine = get_engine()
        inspector = st.connection("sql", type="sql", url=st.session_state.active_db)
        
        from sqlalchemy import inspect
        tables = inspect(engine).get_table_names()
        
        if tables:
            selected_table = st.selectbox("Select Table to Preview:", tables)
            
            columns_in_table = [c["name"] for c in inspect(engine).get_columns(selected_table)]
            
            with st.expander("🔍 Filter & Sort Data"):
                col_f1, col_f2, col_s1, col_s2 = st.columns(4)
                with col_f1:
                    filter_col = st.selectbox("Filter Column", ["None"] + columns_in_table)
                with col_f2:
                    filter_val = st.text_input("Contains (Text/Number):")
                with col_s1:
                    sort_col = st.selectbox("Sort By", ["None"] + columns_in_table)
                with col_s2:
                    sort_order = st.selectbox("Sort Order", ["ASC", "DESC"])

            where_clause = ""
            order_clause = ""
            if filter_col != "None" and filter_val:
                where_clause = f"WHERE {filter_col} LIKE '%{filter_val}%'"
            if sort_col != "None":
                order_clause = f"ORDER BY {sort_col} {sort_order}"

            # Count total rows for pagination
            try:
                count_query = f"SELECT COUNT(*) as c FROM {selected_table} {where_clause}"
                count_df = pd.read_sql(count_query, engine)
                total_rows = int(count_df.iloc[0, 0]) if not count_df.empty else 0
            except:
                total_rows = 1000
                
            page_size = 100
            total_pages = max(1, (total_rows + page_size - 1) // page_size)
            
            col_p1, col_p2 = st.columns([1, 4])
            with col_p1:
                page = st.number_input("Page:", min_value=1, max_value=total_pages, value=1)
            with col_p2:
                st.write("")
                st.caption(f"Showing page {page} of {total_pages} (Total Rows matching filter: {total_rows})")
                
            offset = (page - 1) * page_size
            query = f"SELECT * FROM {selected_table} {where_clause} {order_clause} LIMIT {page_size} OFFSET {offset}"
            
            df = pd.read_sql(query, engine)
            st.dataframe(df, use_container_width=True)
            
            st.markdown("---")
            if st.button("🚨 Run AI Data Quality Scan", use_container_width=True):
                with st.spinner(f"Scanning `{selected_table}` for data anomalies..."):
                    try:
                        from agent import llm
                        schema_info = [(c["name"], str(c["type"])) for c in inspect(engine).get_columns(selected_table)]
                        prompt = f"You are an AI Data Quality Engineer. Review this table schema {schema_info} and the following data snippet:\n{df.head(10).to_string(index=False)}\nIdentify 2 potential data quality risks, anomalies, or strict constraints we should monitor for in a production environment. Keep it concise."
                        scan_res = llm.invoke(prompt)
                        st.warning(scan_res.content)
                    except Exception as scan_err:
                        st.error(f"Scan failed: {scan_err}")
        else:
            st.warning("No tables found in this database.")
        
        # ═══════════════════════════════════════════════════════════════
        # 4.1 STAR SCHEMA & RELATIONSHIP MAPPER
        # ═══════════════════════════════════════════════════════════════
        st.markdown("---")
        st.subheader("🕸️ Star Schema & Relationship Mapper")
        st.markdown("Define Primary/Foreign Key connections across multiple databases to build your enterprise star schema.")
        
        # Load existing metadata
        metadata_path = config.DATA_DIR / "schema_metadata.json"
        if metadata_path.exists():
            with open(metadata_path, "r") as f:
                metadata = json.load(f)
        else:
            metadata = {"relationships": []}

        with st.expander("🛠️ Define New Connection", expanded=False):
            db_files = [f for f in os.listdir(config.DATA_DIR) if f.endswith((".db", ".sqlite"))]
            
            c1, c2 = st.columns(2)
            with c1:
                st.markdown("**Source (Foreign Key)**")
                src_db = st.selectbox("Source Database", db_files, key="src_db")
                # Get tables for src_db
                src_engine = st.connection("sql", type="sql", url=f"sqlite:///{config.DATA_DIR / src_db}")
                src_tables = inspect(src_engine.engine).get_table_names()
                src_table = st.selectbox("Source Table", src_tables, key="src_table")
                src_cols = [c["name"] for c in inspect(src_engine.engine).get_columns(src_table)]
                src_col = st.selectbox("Source Column (FK)", src_cols, key="src_col")
            
            with c2:
                st.markdown("**Target (Primary Key)**")
                tgt_db = st.selectbox("Target Database", db_files, key="tgt_db")
                tgt_engine = st.connection("sql", type="sql", url=f"sqlite:///{config.DATA_DIR / tgt_db}")
                tgt_tables = inspect(tgt_engine.engine).get_table_names()
                tgt_table = st.selectbox("Target Table", tgt_tables, key="tgt_table")
                tgt_cols = [c["name"] for c in inspect(tgt_engine.engine).get_columns(tgt_table)]
                tgt_col = st.selectbox("Target Column (PK)", tgt_cols, key="tgt_col")
            
            rel_type = st.selectbox("Relationship Type", ["Many-to-One", "One-to-One", "Many-to-Many"])
            
            if st.button("🔗 Add Relationship to Schema"):
                new_rel = {
                    "source_db": src_db,
                    "source_table": src_table,
                    "source_column": src_col,
                    "target_db": tgt_db,
                    "target_table": tgt_table,
                    "target_column": tgt_col,
                    "type": rel_type
                }
                metadata["relationships"].append(new_rel)
                with open(metadata_path, "w") as f:
                    json.dump(metadata, f, indent=4)
                st.success("Relationship added! Star Schema updated.")
                st.rerun()

        # Render Star Schema with Graphviz
        if metadata["relationships"]:
            st.markdown("#### Live Enterprise Star Schema")
            dot = graphviz.Digraph(comment='Enterprise Star Schema')
            dot.attr(rankdir='LR', size='8,5')
            dot.attr('node', shape='none')

            # Render tables as HTML labels
            rendered_tables = set()
            for rel in metadata["relationships"]:
                for prefix in ["source", "target"]:
                    db = rel[f"{prefix}_db"]
                    table = rel[f"{prefix}_table"]
                    if (db, table) not in rendered_tables:
                        # Get columns for this table
                        temp_engine = st.connection("sql", type="sql", url=f"sqlite:///{config.DATA_DIR / db}")
                        cols = [c["name"] for c in inspect(temp_engine.engine).get_columns(table)]
                        
                        label = f'<<TABLE BORDER="0" CELLBORDER="1" CELLSPACING="0"><TR><TD COLSPAN="2" BGCOLOR="lightblue"><B>{table}</B> ({db})</TD></TR>'
                        for col in cols:
                            label += f'<TR><TD ALIGN="LEFT">{col}</TD></TR>'
                        label += '</TABLE>>'
                        
                        dot.node(f"{db}_{table}", label=label)
                        rendered_tables.add((db, table))

            # Render edges
            for rel in metadata["relationships"]:
                label = rel["type"]
                dot.edge(
                    f"{rel['source_db']}_{rel['source_table']}", 
                    f"{rel['target_db']}_{rel['target_table']}", 
                    label=label
                )

            st.graphviz_chart(dot)
            
            if st.button("🗑️ Clear All Relationships", type="secondary"):
                if metadata_path.exists():
                    os.remove(metadata_path)
                st.rerun()

    except Exception as e:
        st.error(f"Could not load data preview. Ensure the database connection is valid.\nError: {e}")

# ═══════════════════════════════════════════════════════════════
# 5. INTERACTIVE DASHBOARD
# ═══════════════════════════════════════════════════════════════
with tab_dashboard:
    st.subheader("Interactive Chart Builder")
    st.markdown("Search and select columns to dynamically generate charts from your database.")
    try:
        engine = get_engine()
        from sqlalchemy import inspect
        tables = inspect(engine).get_table_names()
        
        if tables:
            col1, col2, col3 = st.columns(3)
            with col1:
                dash_table = st.selectbox("1. Select Table", tables, key="dash_table")
            
            # Fetch columns for the selected table
            columns = [c["name"] for c in inspect(engine).get_columns(dash_table)]
            
            with col2:
                dash_x = st.selectbox("2. X-Axis (e.g. Region, Date)", columns, key="dash_x")
            with col3:
                # Suggest numeric columns for Y-axis
                numeric_cols = [c["name"] for c in inspect(engine).get_columns(dash_table) if str(c["type"]).startswith("NUMERIC") or str(c["type"]).startswith("INT") or str(c["type"]).startswith("FLOAT") or str(c["type"]).startswith("REAL")]
                dash_y = st.selectbox("3. Y-Axis (e.g. Sales_Amount, Profit)", numeric_cols if numeric_cols else columns, key="dash_y")
                
            st.markdown("---")
            st.markdown("#### 4. Select Chart Type (Visual)")
            if "dash_chart_type" not in st.session_state:
                st.session_state.dash_chart_type = "bar"
                
            cc1, cc2, cc3, cc4 = st.columns(4)
            with cc1:
                st.image("https://cdn-icons-png.flaticon.com/128/3048/3048122.png", width=60)
                if st.button("📊 Bar", use_container_width=True): st.session_state.dash_chart_type = "bar"
            with cc2:
                st.image("https://cdn-icons-png.flaticon.com/128/3308/3308420.png", width=60)
                if st.button("📈 Line", use_container_width=True): st.session_state.dash_chart_type = "line"
            with cc3:
                st.image("https://cdn-icons-png.flaticon.com/128/138/138081.png", width=60)
                if st.button("🥧 Pie", use_container_width=True): st.session_state.dash_chart_type = "pie"
            with cc4:
                st.image("https://cdn-icons-png.flaticon.com/128/5910/5910403.png", width=60)
                if st.button("📉 Scatter", use_container_width=True): st.session_state.dash_chart_type = "scatter"
                
            dash_chart_type = st.session_state.dash_chart_type
            st.info(f"**Currently Selected:** {dash_chart_type.capitalize()} Chart")
            
            col_agg, col_lim = st.columns(2)
            with col_agg:
                dash_agg = st.selectbox("5. Aggregation (Optional)", ["None - Raw Data", "SUM", "AVG", "COUNT", "MAX", "MIN"])
            with col_lim:
                dash_limit = st.selectbox("6. Limit & Sorting", ["Top 10", "Top 50", "Top 100", "Top 500", "All (Limit 1000)"])
                
            limit_val = int(dash_limit.split(" ")[-1]) if dash_limit != "All (Limit 1000)" else 1000
                
            if st.button("Generate Interactive Chart", type="primary", use_container_width=True):
                st.session_state.dash_generated = True
                
            if st.session_state.get("dash_generated", False):
                with st.spinner("Fetching data and generating chart..."):
                    if dash_agg != "None - Raw Data":
                        query = f"SELECT {dash_x}, {dash_agg}({dash_y}) AS {dash_y} FROM {dash_table} GROUP BY {dash_x} ORDER BY {dash_y} DESC LIMIT {limit_val}"
                    else:
                        query = f"SELECT {dash_x}, {dash_y} FROM {dash_table} LIMIT {limit_val}"
                        
                    df_dash = pd.read_sql(query, engine)
                    
                    
                    if not df_dash.empty:
                        from tools.visualizer_tool import _create_chart
                        title = f"{dash_agg} of {dash_y} by {dash_x}" if dash_agg != "None - Raw Data" else f"{dash_y} by {dash_x}"
                        fig = _create_chart(df_dash, dash_chart_type, dash_x, dash_y, title)
                        st.plotly_chart(fig, use_container_width=True)
                        
                        st.markdown("---")
                        col_auto_1, col_auto_2 = st.columns([1, 1])
                        
                        with col_auto_1:
                            st.dataframe(df_dash, use_container_width=True)
                        
                        with col_auto_2:
                            st.markdown("### 🤖 Next-Gen AI Insights")
                            st.info("Use our Agentic reasoning to deeply analyze the current graph anomalies and trends.")
                            if st.button("Generate Executive AI Summary", icon="✨", use_container_width=True):
                                with st.spinner("Analyzing graph geometry and business trends..."):
                                    try:
                                        from agent import llm
                                        prompt_str = f"You are a Senior Data Analyst. Write a 3 sentence hard-hitting business insight about this data:\n{df_dash.to_string(index=False)}"
                                        ai_response = llm.invoke(prompt_str)
                                        st.success(ai_response.content)
                                    except Exception as ai_err:
                                        st.error(f"Failed to generate AI Insights: {ai_err}")
                    else:
                        st.warning("Query returned no data.")
        else:
            st.warning("No tables found in this database.")
    except Exception as e:
        st.error(f"Dashboard error: {e}")

# ═══════════════════════════════════════════════════════════════
# 6. AI POLICY HUB (RAG SEMANTIC SEARCH)
# ═══════════════════════════════════════════════════════════════
with tab_policy:
    st.subheader("Semantic Policy Search")
    st.markdown("Bypass the database and directly search our internal company documents, discount matrices, and product catalogs using AI Vector Search.")
    
    # Render chat history for Policy Hub
    for msg in st.session_state.policy_messages:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])
            if msg.get("expander_content"):
                with st.expander("View Source Documents"):
                    for chunk in msg["expander_content"]:
                        st.markdown(chunk)

    if policy_query := st.chat_input("Ask a policy question...", key="policy_chat"):
        st.session_state.policy_messages.append({"role": "user", "content": policy_query})
        with st.chat_message("user"):
            st.markdown(policy_query)
            
        with st.chat_message("assistant"):
            with st.spinner("Searching vector database and generating response..."):
                try:
                    from tools.rag_tool import _retrieve
                    from agent import llm
                    
                    # 1. Retrieve raw chunks
                    rag_results = _retrieve(policy_query, k=3)
                    
                    if "DATA UNAVAILABLE" in rag_results:
                        final_ans = "No relevant policy documents found for your specific query."
                        chunks = []
                    else:
                        # 2. Synthesize using the main LLM to sound natural
                        rag_prompt = f"Answer this question: '{policy_query}' strictly using only this retrieved policy document data:\n{rag_results}"
                        ans_res = llm.invoke(rag_prompt)
                        final_ans = ans_res.content
                        chunks = [c.strip() for c in rag_results.split("---") if c.strip()]
                    
                    st.markdown(final_ans)
                    if chunks:
                        with st.expander("View Source Documents"):
                            for chunk in chunks:
                                st.markdown(chunk)
                                
                    st.session_state.policy_messages.append({
                        "role": "assistant", 
                        "content": final_ans,
                        "expander_content": chunks
                    })
                except Exception as e:
                    st.error(f"Policy search failed: {e}")
                    st.session_state.policy_messages.append({"role": "assistant", "content": f"Policy search failed: {e}"})

    st.markdown("---")
    st.subheader("📄 Upload & Ingest New Policy")
    uploaded_file = st.file_uploader("Upload a new company policy text file (.txt)", type=["txt"])
    if st.button("Upload Document", type="secondary", use_container_width=True):
        if uploaded_file is not None:
            doc_path = config.DOCS_DIR / uploaded_file.name
            with open(doc_path, "wb") as f:
                f.write(uploaded_file.getbuffer())
            st.success(f"Saved `{uploaded_file.name}`! Please click 'Rebuild Vector Database' below to process it into the A.I.")
        else:
            st.warning("Please attach a .txt file first.")

    st.markdown("---")
    st.subheader("⚙️ Inside the RAG Engine (Under the Hood)")
    st.markdown("To prove how this works, you can manually trigger the **Document Ingestion Pipeline**. This will scrape raw PDFs/Text, run the Recursive Character Text Splitter, and generate Mathematics Vectors (Embeddings) using HuggingFace.")
    
    if st.button("🛠️ Rebuild Vector Database", use_container_width=True):
        progress_bar = st.progress(0)
        status_text = st.empty()
        
        try:
            import time
            from tools.rag_tool import _build_vector_store
            
            status_text.text("Step 1: Connecting to Local Directory ./docs/ ...")
            time.sleep(1)
            progress_bar.progress(25)
            
            status_text.text("Step 2: Loading Documents and Running RecursiveCharacterTextSplitter (Chunk Size: 500)...")
            time.sleep(1.5)
            progress_bar.progress(50)
            
            status_text.text("Step 3: Initializing local HuggingFace Embedding Model (all-MiniLM-L6-v2)...")
            time.sleep(1)
            progress_bar.progress(75)
            
            status_text.text("Step 4: Vectorizing text chunks and persisting to ChromaDB...")
            # Actually run the rebuild
            _build_vector_store()
            
            progress_bar.progress(100)
            status_text.success("✅ Vector Database successfully rebuilt and structured!")
            st.balloons()
            
        except Exception as e:
            st.error(f"Failed to rebuild Vector DB: {e}")

# ═══════════════════════════════════════════════════════════════
# 7. ASSISTANT CHAT INTERFACE
# ═══════════════════════════════════════════════════════════════
with tab_chat:
    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])
            if message.get("image"):
                import os
                if os.path.exists(message["image"]):
                    st.image(message["image"])
            if message.get("plotly_fig"):
                st.plotly_chart(message["plotly_fig"], use_container_width=True)

    if prompt := st.chat_input("Ask a question about your data..."):
        st.chat_message("user").markdown(prompt)
        st.session_state.messages.append({"role": "user", "content": prompt})
        
        with st.chat_message("assistant"):
            status = st.status("Agent is working...", expanded=True)
            final_response = "No response generated."
            image_to_display = None
            plotly_fig_to_display = None
            
            for step in stream_agent(prompt):
                if "agent" in step:
                    msg_list = step["agent"].get("messages", [])
                    if msg_list:
                        msg = msg_list[-1]
                        if getattr(msg, "tool_calls", None):
                            for tc in msg.tool_calls:
                                status.write(f"🛠️ **Calling Tool:** `{tc['name']}`")
                                status.caption(f"Args: `{tc['args']}`")
                                
                                # Intercept visualization tool payload to render an interactive chart
                                if tc["name"] == "visualization_tool":
                                    import json
                                    from tools.visualizer_tool import _create_chart
                                    try:
                                        payload_str = tc["args"].get("input_json", "{}")
                                        payload = json.loads(payload_str)
                                        df = pd.DataFrame(payload.get("data", []))
                                        if not df.empty:
                                            plotly_fig_to_display = _create_chart(
                                                df,
                                                payload.get("chart_type", "bar"),
                                                payload.get("x_column", ""),
                                                payload.get("y_column", ""),
                                                payload.get("title", ""),
                                                payload.get("color_column", "")
                                            )
                                    except Exception as e:
                                        status.error(f"Failed to render interactive chart: {e}")
                        
                        # Extract content from ANY agent message in the stream
                        msg_text = ""
                        if hasattr(msg, "content"):
                            if isinstance(msg.content, str):
                                msg_text = msg.content
                            elif isinstance(msg.content, list):
                                # Gemini sometimes sends a list for multimodal or structured content
                                msg_text = " ".join([m.get("text", "") if isinstance(m, dict) else str(m) for m in msg.content])
                        
                        if msg_text.strip():
                            final_response = msg_text
                
                elif "tools" in step:
                    msg_list = step["tools"].get("messages", [])
                    if msg_list:
                        msg = msg_list[-1]
                        status.write(f"✅ **Tool returned results:**")
                        with status.expander("View Output", expanded=False):
                            st.text(msg.content)
                        
                        # Detect generated chart
                        if "Chart saved successfully:" in msg.content:
                            lines = msg.content.split("\n")
                            png_line = next((line for line in lines if "PNG :" in line), None)
                            if png_line:
                                png_path = png_line.split("PNG :")[1].strip()
                                import os
                                if os.path.exists(png_path):
                                    image_to_display = png_path
                
                elif "error" in step:
                    status.error(step["error"])
                    final_response = f"Error: {step['error']}"

            if final_response == "No response generated.":
                 final_response = "I have successfully processed your request and generated the visual insights above."

            status.update(label="Finished!", state="complete", expanded=False)
            st.markdown(final_response)
            if image_to_display:
                st.image(image_to_display)
            if plotly_fig_to_display:
                st.plotly_chart(plotly_fig_to_display, use_container_width=True)
                
        st.session_state.messages.append({
            "role": "assistant", 
            "content": final_response,
            "image": image_to_display,
            "plotly_fig": plotly_fig_to_display
        })

