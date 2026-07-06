"""
eval_sql_structure.py — SQL Query Structural Correctness Evaluator
==================================================================
This script goes beyond checking if an AI query returned the right answer.
It analyzes whether the query itself is structurally and logically correct
by grading it across 5 dimensions:

  1. TABLES: Did it join the correct tables?
  2. COLUMNS: Did it select/aggregate the correct columns?
  3. JOINS: Is the JOIN logic correct (right keys, right type)?
  4. AGGREGATION: Is the GROUP BY / aggregation function correct?
  5. FILTERS/ORDERING: Are WHERE, HAVING, ORDER BY, LIMIT correct?

Each dimension is scored 0–2 by an LLM judge.

BONUS DETERMINISTIC METRICS:
  - Precision@Tables: Of the tables the AI used, what % were actually needed?
  - Recall@Tables: Of the tables that were needed, what % did the AI include?

Usage:
  python evals/eval_sql_structure.py
"""

import os
import sys
import json
import re
from collections import defaultdict
from textwrap import dedent

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from agent import run_agent, clear_memory
from evals.eval_generator import get_llm_judge


DIMENSIONS = ["tables", "columns", "joins", "aggregation", "filters_ordering"]


def extract_sql_from_response(response: str) -> str:
    """Extracts SQL code block from the AI's response."""
    match = re.search(r"```sql\n(.*?)\n```", response, re.DOTALL | re.IGNORECASE)
    if match:
        return match.group(1).strip()
    return ""


def extract_table_names(sql: str) -> set:
    """
    Deterministically extracts all table names referenced in a SQL query.
    Finds words immediately after FROM and JOIN keywords.
    Returns a lowercase set for case-insensitive comparison.
    """
    # Match: FROM/JOIN <tablename> optionally followed by alias
    pattern = re.findall(
        r'\b(?:FROM|JOIN)\s+([a-zA-Z_][a-zA-Z0-9_]*)',
        sql, re.IGNORECASE
    )
    return {t.lower() for t in pattern}


def compute_table_precision_recall(expected_sql: str, generated_sql: str) -> tuple:
    """
    Computes Precision@Tables and Recall@Tables.

    Precision = |AI_tables ∩ Expected_tables| / |AI_tables|
      → Of the tables the AI queried, what fraction were actually needed?
      → Low precision means the AI joined EXTRA unnecessary tables.

    Recall = |AI_tables ∩ Expected_tables| / |Expected_tables|
      → Of the tables that were needed, what fraction did the AI include?
      → Low recall means the AI MISSED critical tables.
    """
    expected_tables = extract_table_names(expected_sql)
    generated_tables = extract_table_names(generated_sql)

    if not generated_tables:
        return 0.0, 0.0

    intersection = expected_tables & generated_tables
    precision = len(intersection) / len(generated_tables) if generated_tables else 0.0
    recall    = len(intersection) / len(expected_tables)  if expected_tables    else 0.0

    return round(precision, 2), round(recall, 2)


def judge_sql_structure(llm, question: str, expected_sql: str, generated_sql: str) -> dict:
    """
    Uses the LLM to grade the generated SQL on 5 structural dimensions.
    Returns a dict of scores and an explanation for each.
    """
    judge_prompt = dedent(f"""
    You are an expert SQL database reviewer. Your job is to evaluate whether a "Generated SQL" query is structurally and logically correct compared to an "Expected SQL" query.

    The question the user asked was:
    "{question}"

    Expected SQL (reference answer):
    {expected_sql}

    Generated SQL (AI output to evaluate):
    {generated_sql}

    Grade the Generated SQL on each of the following 5 dimensions.
    For each dimension, give a score and a short one-line reason.
    Score meanings: 2 = Correct, 1 = Partially correct, 0 = Wrong or missing.

    Output ONLY valid JSON in this exact format:
    {{
      "tables": {{"score": <0|1|2>, "reason": "<one line>"}},
      "columns": {{"score": <0|1|2>, "reason": "<one line>"}},
      "joins": {{"score": <0|1|2>, "reason": "<one line>"}},
      "aggregation": {{"score": <0|1|2>, "reason": "<one line>"}},
      "filters_ordering": {{"score": <0|1|2>, "reason": "<one line>"}}
    }}
    """).strip()

    try:
        response = llm.invoke(judge_prompt).content.strip()
        response = re.sub(r"```json\n?|```", "", response).strip()
        scores = json.loads(response)
        return scores
    except Exception as e:
        print(f"  [Error] LLM Judge failed to parse: {e}")
        return {d: {"score": 0, "reason": "Parse error"} for d in DIMENSIONS}


def print_score_row(dimension: str, score: int, reason: str):
    """Pretty-print a single dimension score."""
    icons = {2: "[PASS]", 1: "[WARN]", 0: "[FAIL]"}
    label = {2: "Full", 1: "Partial", 0: "None"}
    print(f"  {icons[score]} {dimension:<20} [{label[score]}] {reason}")


def evaluate_sql_structure(dataset_path: str):
    print("--- Starting SQL Structural Correctness Evaluation ---\n")

    with open(dataset_path, "r", encoding="utf-8") as f:
        dataset = json.load(f)

    llm = get_llm_judge()
    total_questions = len(dataset)
    grand_total_score = 0.0
    MAX_SCORE_PER_QUESTION = 10  # 5 dimensions × max 2

    # Accumulators for dimension-wise summary and P/R
    dim_totals   = defaultdict(int)   # sum of raw scores (0-2) per dimension
    total_precision = 0.0
    total_recall    = 0.0

    for i, test_case in enumerate(dataset):
        question     = test_case["question"]
        expected_sql = test_case["expected_sql"]

        print(f"Q{i+1}: {question}")

        # 1. Generate the AI's SQL
        clear_memory()
        response = run_agent(question)
        generated_sql = extract_sql_from_response(response)

        if not generated_sql:
            print(f"  ❌ No SQL was generated by the agent.\n")
            # Count as 0 for all dimensions
            for d in DIMENSIONS:
                dim_totals[d] += 0
            continue

        print(f"  Expected SQL : {expected_sql}")
        print(f"  Generated SQL: {generated_sql}")
        print()

        # 2. Deterministic Precision & Recall on table names
        precision, recall = compute_table_precision_recall(expected_sql, generated_sql)
        total_precision += precision
        total_recall    += recall

        exp_tables = extract_table_names(expected_sql)
        gen_tables = extract_table_names(generated_sql)
        missing    = exp_tables - gen_tables
        extra      = gen_tables - exp_tables

        prec_icon = "[PASS]" if precision == 1.0 else ("[WARN]" if precision > 0 else "[FAIL]")
        rec_icon = "[PASS]" if recall == 1.0 else ("[WARN]" if recall > 0 else "[FAIL]")

        print(f"  {prec_icon} Precision@Tables     : {precision:.2f}  "
              f"(AI used: {sorted(gen_tables)})")
        print(f"  {rec_icon} Recall@Tables        : {recall:.2f}  "
              f"(Expected: {sorted(exp_tables)}"
              + (f", Missing: {sorted(missing)}" if missing else "") + ")")
        if extra:
            print(f"  [WARN]  Extra tables joined  : {sorted(extra)}")
        print()

        # 3. LLM Judge — 5 structural dimensions
        scores = judge_sql_structure(llm, question, expected_sql, generated_sql)

        question_total = 0
        for dimension in DIMENSIONS:
            data      = scores.get(dimension, {"score": 0, "reason": "N/A"})
            dim_score = data.get("score", 0)
            dim_reason= data.get("reason", "N/A")
            question_total    += dim_score
            dim_totals[dimension] += dim_score
            print_score_row(dimension.replace("_", " ").title(), dim_score, dim_reason)

        # 4. Per-question overall score
        normalized = question_total / MAX_SCORE_PER_QUESTION
        grand_total_score += normalized
        print(f"\n  Overall Structural Score: {question_total}/{MAX_SCORE_PER_QUESTION} ({normalized:.0%})\n")
        print("-" * 60)

    # ─────────────────────────────────────────────────
    # SUMMARY: Dimension-wise mark distribution
    # ─────────────────────────────────────────────────
    avg_structural_score = grand_total_score / total_questions
    avg_precision        = total_precision   / total_questions
    avg_recall           = total_recall      / total_questions

    print(f"\n{'=' * 60}")
    print(f"  SQL STRUCTURAL EVALUATION — FINAL SUMMARY")
    print(f"{'=' * 60}")

    # Dimension-wise table
    print(f"\n  Dimension-Wise Average Score (out of 2.0):\n")
    print(f"  {'Dimension':<22} {'Avg Score':>10}  {'Bar':}")
    print(f"  {'-'*22} {'-'*10}  {'-'*20}")
    for dim in DIMENSIONS:
        avg = dim_totals[dim] / total_questions
        bar_filled = int((avg / 2.0) * 20)
        bar = "#" * bar_filled + "." * (20 - bar_filled)
        icon = "[PASS]" if avg >= 1.8 else ("[WARN]" if avg >= 1.0 else "[FAIL]")
        print(f"  {icon} {dim.replace('_', ' ').title():<20} {avg:>6.2f}/2.0  [{bar}]")

    print(f"\n  Deterministic Table Metrics (Pure Math):")
    prec_icon = "[PASS]" if avg_precision >= 0.9 else ("[WARN]" if avg_precision >= 0.6 else "[FAIL]")
    rec_icon  = "[PASS]" if avg_recall   >= 0.9 else ("[WARN]" if avg_recall   >= 0.6 else "[FAIL]")
    print(f"  {prec_icon} Avg Precision@Tables  : {avg_precision:.2f}  "
          f"(Did AI avoid unnecessary tables?)")
    print(f"  {rec_icon} Avg Recall@Tables     : {avg_recall:.2f}  "
          f"(Did AI include ALL required tables?)")

    print(f"\n  Overall Structural Score  : {avg_structural_score:.2f} ({avg_structural_score:.0%})")
    print(f"{'=' * 60}\n")

    return avg_structural_score


if __name__ == "__main__":
    dataset_file = os.path.join(os.path.dirname(__file__), "eval_sql_dataset.json")
    evaluate_sql_structure(dataset_file)
