import sys
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.append(str(BASE_DIR))

from agent import run_agent

report_prompt = (
    "You are an elite Business Intelligence Analyst. Your mandate is to write a masterclass, ultra-detailed Executive Sales Report in pure HTML format. "
    "Use the visualization_tool to generate ONE bar chart. "
    "Return ONLY pristine, valid raw HTML code."
)

res = run_agent(report_prompt)
print("--- OUTPUT ---")
print(res[:200] if len(res) > 200 else res)
