"""
run_queries.py — Run all gold standard queries and display results
==================================================================
Runs every expected_sql in eval_sql_dataset.json directly against
Supabase and prints the results as a plain-text table. No agent involved.

Usage:
  python evals/run_queries.py
"""

import os
import sys
import json
import pandas as pd
from sqlalchemy import text

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from tools.sql_tool import get_engine


def print_df(df: pd.DataFrame, max_rows: int = 10):
    """Print dataframe as a plain ASCII table."""
    if df.empty:
        print("  (no rows returned)")
        return

    display_df = df.head(max_rows)
    col_widths = [
        max(len(str(col)), max((len(str(v)) for v in display_df[col]), default=0))
        for col in display_df.columns
    ]

    divider = "  +" + "+".join("-" * (w + 2) for w in col_widths) + "+"
    header  = "  | " + " | ".join(str(col).ljust(w) for col, w in zip(display_df.columns, col_widths)) + " |"

    print(divider)
    print(header)
    print(divider)
    for _, row in display_df.iterrows():
        line = "  | " + " | ".join(str(v).ljust(w) for v, w in zip(row, col_widths)) + " |"
        print(line)
    print(divider)

    if len(df) > max_rows:
        print(f"  ... {len(df) - max_rows} more rows (showing top {max_rows})")
    print(f"  Total rows returned: {len(df)}")


def main():
    dataset_file = os.path.join(os.path.dirname(__file__), "eval_sql_dataset.json")
    with open(dataset_file, "r", encoding="utf-8") as f:
        dataset = json.load(f)

    engine = get_engine()
    total  = len(dataset)
    passed = 0
    failed = 0

    print("=" * 70)
    print(f"  RUNNING ALL {total} GOLD STANDARD QUERIES AGAINST SUPABASE")
    print("=" * 70)

    for i, test_case in enumerate(dataset):
        question = test_case["question"]
        sql      = test_case["expected_sql"]

        print(f"\nQ{i+1}/{total}: {question}")
        print(f"  SQL: {sql[:120]}{'...' if len(sql) > 120 else ''}\n")

        try:
            with engine.connect() as conn:
                df = pd.read_sql(text(sql), conn)
            print_df(df, max_rows=10)
            print(f"  [PASS]")
            passed += 1
        except Exception as e:
            print(f"  [FAIL] {e}")
            failed += 1

        print("-" * 70)

    print(f"\n{'=' * 70}")
    print(f"  SUMMARY: {passed}/{total} queries passed  |  {failed} failed")
    print(f"{'=' * 70}\n")


if __name__ == "__main__":
    main()
