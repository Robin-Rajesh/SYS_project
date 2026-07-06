"""
generate_pdf.py — Generate PDF report from existing eval_report.xlsx
=====================================================================
Reads the Summary sheet from outputs/eval_report.xlsx and produces
outputs/eval_validation_report.pdf — without re-running any agent queries.

Usage:
  python evals/generate_pdf.py
"""

import os
import sys
from datetime import datetime

import pandas as pd

OUTPUT_DIR = os.path.join(os.path.dirname(__file__), "..", "outputs")
EXCEL_PATH = os.path.join(OUTPUT_DIR, "eval_report.xlsx")
PDF_PATH   = os.path.join(OUTPUT_DIR, "eval_validation_report.pdf")


def safe_para(text: str, max_chars: int = 2000) -> str:
    """Escape XML special chars and truncate for safe use in Paragraph."""
    text = str(text)
    if len(text) > max_chars:
        text = text[:max_chars] + "\n... [truncated]"
    return (text
            .replace("&", "&amp;")
            .replace("<", "&lt;")
            .replace(">", "&gt;")
            .replace("\n", "<br/>"))


def sort_output_text(text: str) -> str:
    """
    Sort the data rows of a pipe-delimited query output so both proposed
    and generated outputs appear in the same canonical order.
    Header, divider line, and footnotes are kept in place; only data rows sorted.
    """
    text = str(text)
    lines = text.split("\n")
    if len(lines) < 3:
        return text

    header  = lines[0]   # column names
    divider = lines[1]   # dashes

    data_lines = []
    footnotes  = []
    for line in lines[2:]:
        stripped = line.strip()
        if stripped.startswith("...") or stripped.startswith("(Total"):
            footnotes.append(line)
        else:
            data_lines.append(line)

    data_lines.sort()
    return "\n".join([header, divider] + data_lines + footnotes)


def build_pdf(df: pd.DataFrame, path: str):
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.units import cm
    from reportlab.lib import colors
    from reportlab.platypus import (
        SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle,
        PageBreak, HRFlowable, KeepTogether,
    )

    PAGE = A4
    W, _H = PAGE

    DOC = SimpleDocTemplate(
        path,
        pagesize=PAGE,
        leftMargin=1.5*cm, rightMargin=1.5*cm,
        topMargin=2*cm,   bottomMargin=2*cm,
    )

    styles = getSampleStyleSheet()
    usable_width = W - 3*cm

    PASS_COLOR = colors.HexColor("#C6EFCE")
    FAIL_COLOR = colors.HexColor("#FFC7CE")
    ERR_COLOR  = colors.HexColor("#FFEB9C")
    HDR_COLOR  = colors.HexColor("#1F3864")

    title_style = ParagraphStyle(
        "ReportTitle", parent=styles["Heading1"],
        fontSize=16, textColor=HDR_COLOR, spaceAfter=6,
    )
    h2_style = ParagraphStyle(
        "QHead", parent=styles["Heading2"],
        fontSize=10, textColor=colors.HexColor("#2E4057"),
        spaceBefore=6, spaceAfter=3,
    )
    label_style = ParagraphStyle(
        "SLabel", parent=styles["Normal"],
        fontSize=8, fontName="Helvetica-Bold",
        textColor=colors.HexColor("#333333"),
        spaceBefore=4, spaceAfter=1,
    )
    mono_style = ParagraphStyle(
        "MonoBlock", parent=styles["Code"],
        fontSize=6.5, leading=8.5,
        backColor=colors.HexColor("#F7F7F7"),
        leftIndent=4, rightIndent=4,
        spaceBefore=1, spaceAfter=3,
    )
    normal_style = ParagraphStyle(
        "NormalTxt", parent=styles["Normal"],
        fontSize=9, leading=12,
    )

    def section(label, content):
        return [
            Paragraph(label, label_style),
            Paragraph(safe_para(content), mono_style),
        ]

    story = []

    # Cover page
    story.append(Spacer(1, 2*cm))
    story.append(Paragraph("AI Analytics - SQL Evaluation Report", title_style))
    story.append(Paragraph(
        f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M')}  |  "
        f"Total prompts: <b>{len(df)}</b>",
        normal_style,
    ))
    story.append(Spacer(1, 0.5*cm))

    passed = sum(1 for v in df["Results Match"] if str(v).strip().upper() == "PASS")
    failed = sum(1 for v in df["Results Match"] if str(v).strip().upper() == "FAIL")
    errors = len(df) - passed - failed

    cov_data = [
        ["Total Prompts", "Passed", "Failed", "Errors"],
        [str(len(df)), str(passed), str(failed), str(errors)],
    ]
    cov_tbl = Table(cov_data, colWidths=[usable_width / 4] * 4)
    cov_tbl.setStyle(TableStyle([
        ("BACKGROUND",    (0, 0), (-1, 0),  HDR_COLOR),
        ("TEXTCOLOR",     (0, 0), (-1, 0),  colors.white),
        ("FONTNAME",      (0, 0), (-1, 0),  "Helvetica-Bold"),
        ("FONTSIZE",      (0, 0), (-1, -1), 11),
        ("ALIGN",         (0, 0), (-1, -1), "CENTER"),
        ("BACKGROUND",    (1, 1), (1, 1),   PASS_COLOR),
        ("BACKGROUND",    (2, 1), (2, 1),   FAIL_COLOR),
        ("BACKGROUND",    (3, 1), (3, 1),   ERR_COLOR),
        ("GRID",          (0, 0), (-1, -1), 0.5, colors.grey),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
        ("TOPPADDING",    (0, 0), (-1, -1), 8),
    ]))
    story.append(cov_tbl)
    story.append(PageBreak())

    # Per-question pages
    for _, row in df.iterrows():
        match = str(row.get("Results Match", "")).strip().upper()
        if match == "PASS":
            badge_color, badge_text = PASS_COLOR, "PASS"
        elif match == "FAIL":
            badge_color, badge_text = FAIL_COLOR, "FAIL"
        else:
            badge_color, badge_text = ERR_COLOR, "ERROR"

        badge_tbl = Table([[badge_text]], colWidths=[3*cm])
        badge_tbl.setStyle(TableStyle([
            ("BACKGROUND",    (0, 0), (-1, -1), badge_color),
            ("ALIGN",         (0, 0), (-1, -1), "CENTER"),
            ("FONTNAME",      (0, 0), (-1, -1), "Helvetica-Bold"),
            ("FONTSIZE",      (0, 0), (-1, -1), 9),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
            ("TOPPADDING",    (0, 0), (-1, -1), 4),
        ]))

        q_num  = row.get("Q#", "?")
        prompt = str(row.get("Prompt", ""))

        story.append(KeepTogether([
            Paragraph(f"Q{q_num}: {safe_para(prompt)}", h2_style),
            HRFlowable(width="100%", thickness=0.8, color=colors.HexColor("#BBBBBB")),
            Spacer(1, 0.15*cm),
            badge_tbl,
            Spacer(1, 0.2*cm),
        ]))

        # Sort both outputs so rows appear in the same order
        proposed_out  = sort_output_text(str(row.get("Proposed SQL Output",  "")))
        generated_out = sort_output_text(str(row.get("Generated SQL Output", "")))

        story.extend(section("Proposed SQL (Expected):",
                             str(row.get("Proposed SQL", ""))))
        story.extend(section("Proposed SQL Output (sorted):", proposed_out))

        story.append(HRFlowable(width="100%", thickness=0.4,
                                color=colors.HexColor("#DDDDDD")))
        story.append(Spacer(1, 0.1*cm))

        story.extend(section("Generated SQL (AI Output):",
                             str(row.get("Generated SQL", ""))))
        story.extend(section("Generated SQL Output (sorted):", generated_out))

        story.append(PageBreak())

    DOC.build(story)
    print(f"PDF saved: {path}")


def main():
    if not os.path.exists(EXCEL_PATH):
        print(f"ERROR: Excel file not found at {EXCEL_PATH}")
        print("Run export_eval_report.py first to generate it.")
        sys.exit(1)

    print(f"Reading Excel from: {EXCEL_PATH}")
    df = pd.read_excel(EXCEL_PATH, sheet_name="Summary")
    print(f"Loaded {len(df)} rows from Summary sheet.")
    print(f"Writing PDF to:     {PDF_PATH}")

    build_pdf(df, PDF_PATH)


if __name__ == "__main__":
    main()
