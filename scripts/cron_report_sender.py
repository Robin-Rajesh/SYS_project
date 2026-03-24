import os
import sys
import smtplib
from email.message import EmailMessage
from pathlib import Path

# Add project root to path so we can import app modules
BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.append(str(BASE_DIR))

import config
from agent import run_agent

def generate_report() -> str:
    print("Generating AI Sales Report. This will take a few minutes...")
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
        
    import re, base64, urllib.parse, os
    def make_html_portable(html_txt):
        def replacer(match):
            path = urllib.parse.unquote(match.group(1)).replace("%3A", ":")
            if os.path.exists(path):
                with open(path, "r", encoding="utf-8", errors="ignore") as f:
                    content = f.read()
                
                b64 = base64.b64encode(content.encode("utf-8")).decode('utf-8')
                return f'src="data:text/html;base64,{b64}"'
            return match.group(0)
            
        html_txt = re.sub(r'src=["\']file:///(.*?)["\']', replacer, html_txt)
        return re.sub(r'>\s+<', '><', html_txt)

    report_content = make_html_portable(report_content)
    return report_content

def send_email(html_content: str):
    print("Preparing to send email...")
    
    if not config.SENDER_EMAIL or not config.SENDER_PASSWORD or not config.RECIPIENT_EMAIL:
        print("ERROR: Missing SMTP email credentials in .env file.")
        print(f"SENDER_EMAIL={config.SENDER_EMAIL}, SENDER_PASSWORD={'***' if config.SENDER_PASSWORD else ''}, RECIPIENT_EMAIL={config.RECIPIENT_EMAIL}")
        return

    msg = EmailMessage()
    msg["Subject"] = "Daily AI Executive Sales Report"
    msg["From"] = config.SENDER_EMAIL
    msg["To"] = config.RECIPIENT_EMAIL

    msg.set_content("Please find the attached AI-generated Sales Report. Download and open the attachment in your web browser (Chrome/Edge) to view the interactive charts.")
    
    msg.add_attachment(
        html_content.encode("utf-8"),
        maintype="text",
        subtype="html",
        filename="Executive_Sales_Report.html"
    )

    try:
        # Note: If security policies block the SMTP connection, you might need to try TLS directly
        server = smtplib.SMTP(config.SMTP_SERVER, config.SMTP_PORT)
        server.ehlo()
        server.starttls()
        server.login(config.SENDER_EMAIL, config.SENDER_PASSWORD)
        server.send_message(msg)
        server.quit()
        print("Email sent successfully!")
    except Exception as e:
        print(f"Failed to send email. Error: {e}")

if __name__ == "__main__":
    # Check if recipient email is passed as a command line argument (from schtasks)
    target_email = sys.argv[1] if len(sys.argv) > 1 else config.RECIPIENT_EMAIL
    
    if not target_email:
        print("ERROR: No recipient email provided. Please set via command line or config.")
        sys.exit(1)

    print(f"Starting scheduled task for: {target_email}")
    report_html = generate_report()
    
    # Temporarily override config.RECIPIENT_EMAIL for this execution
    config.RECIPIENT_EMAIL = target_email
    send_email(report_html)
