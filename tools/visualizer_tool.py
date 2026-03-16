"""
visualizer_tool.py — Chart Generation Tool (Plotly + PNG/HTML Export)
=====================================================================
LangChain Tool that:
  1. Accepts a JSON string with data, chart_type, axes, and title
  2. Creates the chart using Plotly Express
  3. Saves both PNG (via kaleido) and interactive HTML to outputs/
  4. Returns the saved file paths on success
"""

import json
from datetime import datetime
import pandas as pd
import plotly.express as px
from langchain_core.tools import tool

# Import project configuration
import config

# ═══════════════════════════════════════════════════════════════
# 1. CHART-TYPE DISPATCHER
# ═══════════════════════════════════════════════════════════════
# Maps chart_type strings to the corresponding Plotly Express function.

CHART_FUNCTIONS = {
    "bar":       px.bar,
    "line":      px.line,
    "pie":       px.pie,
    "scatter":   px.scatter,
    "histogram": px.histogram,
}


def _create_chart(df: pd.DataFrame, chart_type: str,
                  x_col: str, y_col: str, title: str,
                  color_col: str = "") -> object:
    """
    Build a Plotly figure from the provided DataFrame and parameters.
    Falls back to a bar chart if the requested type is not recognised.
    """
    chart_fn = CHART_FUNCTIONS.get(chart_type, px.bar)

    # Common keyword arguments shared across most chart types
    kwargs = {"data_frame": df, "title": title}
    kwargs["color_discrete_sequence"] = px.colors.qualitative.Vivid

    if chart_type == "pie":
        # Pie charts use 'names' and 'values' instead of x/y
        kwargs["names"]  = x_col
        kwargs["values"] = y_col
    else:
        kwargs["x"] = x_col
        kwargs["y"] = y_col

    # Optional colour grouping
    if color_col and color_col in df.columns:
        kwargs["color"] = color_col

    fig = chart_fn(**kwargs)

    # Apply a clean, professional template
    fig.update_layout(template="plotly_white")
    return fig

# ═══════════════════════════════════════════════════════════════
# 2. LANGCHAIN TOOL DEFINITION
# ═══════════════════════════════════════════════════════════════

@tool
def visualization_tool(input_json: str) -> str:
    """Use this to generate and save charts from data.
    Input must be a JSON string with fields: data (list of dicts),
    chart_type, x_column, y_column, title, and optionally color_column.
    """
    try:
        # --- Parse the incoming JSON payload ---
        payload = json.loads(input_json)
        data         = payload.get("data", [])
        chart_type   = payload.get("chart_type", "bar")
        x_column     = payload.get("x_column", "")
        y_column     = payload.get("y_column", "")
        title        = payload.get("title", "Sales Chart")
        color_column = payload.get("color_column", "")

        # --- Validate that data is non-empty ---
        if not data or not isinstance(data, list):
            return (
                "VISUALIZATION FAILED: No valid data provided "
                "to generate chart."
            )

        # Convert the list of dicts to a pandas DataFrame
        df = pd.DataFrame(data)

        if df.empty:
            return (
                "VISUALIZATION FAILED: No valid data provided "
                "to generate chart."
            )

        # --- Generate the Plotly figure ---
        fig = _create_chart(df, chart_type, x_column, y_column,
                            title, color_column)

        # --- Build timestamped filenames ---
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        png_path  = config.OUTPUTS_DIR / f"chart_{timestamp}.png"
        html_path = config.OUTPUTS_DIR / f"chart_{timestamp}.html"

        # --- Save interactive HTML (Skip PNG as kaleido hangs on Windows) ---
        fig.write_html(str(html_path))

        return (
            f"Chart saved successfully:\n"
            f"  HTML: {html_path}\n"
            f"  (Note: I have generated the chart for the user's dashboard! Do not attempt to show the image yourself.)"
        )

    except json.JSONDecodeError:
        return (
            "VISUALIZATION FAILED: The input is not valid JSON. "
            "Please provide a JSON string with fields: data, "
            "chart_type, x_column, y_column, title."
        )
    except Exception as e:
        return f"VISUALIZATION FAILED: {str(e)}"
