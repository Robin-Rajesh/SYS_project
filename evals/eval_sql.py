import os
import sys
import json
import re
import pandas as pd
from sqlalchemy import text

# Add project root to path so we can import project modules
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from agent import run_agent, clear_memory
from tools.sql_tool import get_engine
from evals.eval_generator import get_llm_judge
from textwrap import dedent


def extract_sql_from_response(response: str) -> str:
    """Extracts SQL code block from the AI's response."""
    match = re.search(r"```sql\n(.*?)\n```", response, re.DOTALL | re.IGNORECASE)
    if match:
        return match.group(1).strip()
    return ""


def print_df_as_table(df: pd.DataFrame, max_rows: int = 10):
    """Pretty-print the top N rows of a dataframe in a bordered box."""
    display_df = df.head(max_rows)
    col_widths = [
        max(len(str(col)), max((len(str(v)) for v in display_df[col]), default=0))
        for col in display_df.columns
    ]

    def make_border(left, mid, fill, right):
        return left + mid.join(fill * (w + 2) for w in col_widths) + right

    header = " | ".join(str(col).ljust(w) for col, w in zip(display_df.columns, col_widths))
    print(f"  {make_border('┌', '┬', '─', '┐')}")
    print(f"  │ {header} │")
    print(f"  {make_border('├', '┼', '─', '┤')}")
    for _, row in display_df.iterrows():
        line = " | ".join(str(v).ljust(w) for v, w in zip(row, col_widths))
        print(f"  │ {line} │")
    print(f"  {make_border('└', '┴', '─', '┘')}")

    if len(df) > max_rows:
        print(f"  ... and {len(df) - max_rows} more rows (showing top {max_rows})")


def evaluate_sql(dataset_path: str):
    print("--- Starting Text-to-SQL Evaluation ---")

    with open(dataset_path, 'r', encoding='utf-8') as f:
        dataset = json.load(f)

    engine = get_engine()
    llm = get_llm_judge()

    total_questions = len(dataset)
    total_execution_accuracy = 0.0
    total_result_accuracy = 0.0
    total_equivalence_accuracy = 0.0

    print(f"Loaded {total_questions} SQL test cases.\n")

    for i, test_case in enumerate(dataset):
        question = test_case["question"]
        expected_sql = test_case["expected_sql"]

        print(f"{'=' * 65}")
        print(f"Q{i+1}: {question}")
        print(f"{'=' * 65}")

        clear_memory()

        # 1. GENERATE SQL USING THE AGENT
        response = run_agent(question)
        generated_sql = extract_sql_from_response(response)

        print(f"\n  [Expected SQL]\n  {expected_sql}\n")
        print(f"  [Generated SQL]\n  {generated_sql}\n")

        if not generated_sql:
            print("  [Metric] Execution Accuracy: 0.00 (No SQL generated)\n")
            continue

        # 2. EXECUTION ACCURACY — Does it run?
        execution_success = False
        generated_df = None

        try:
            with engine.connect() as conn:
                generated_df = pd.read_sql(text(generated_sql), conn)
            execution_success = True
            total_execution_accuracy += 1.0
            print("  [Metric] Execution Accuracy: 1.00 ✅ (Query ran without error)")
        except Exception as e:
            print(f"  [Metric] Execution Accuracy: 0.00 ❌ (Error: {e})")

        # 3. PRINT ACTUAL DATA RESULTS — for client verification
        if execution_success and generated_df is not None:
            print(f"\n  ACTUAL QUERY RESULTS ({len(generated_df)} rows returned):")
            print_df_as_table(generated_df, max_rows=10)
            print()

        # 4. RESULT ACCURACY — Does the data match the expected output?
        if execution_success:
            try:
                with engine.connect() as conn:
                    expected_df = pd.read_sql(text(expected_sql), conn)

                # Compare as a set of string-tuples to ignore column name/order differences
                gen_data = {tuple(str(v) for v in row) for row in generated_df.itertuples(index=False, name=None)}
                exp_data = {tuple(str(v) for v in row) for row in expected_df.itertuples(index=False, name=None)}

                if gen_data == exp_data:
                    total_result_accuracy += 1.0
                    print("  [Metric] Result Accuracy: 1.00 ✅ (Data matches expected output perfectly)")
                else:
                    print("  [Metric] Result Accuracy: 0.00 ❌ (Data does NOT match expected)")
                    print(f"\n  EXPECTED RESULTS (for comparison):")
                    print_df_as_table(expected_df, max_rows=10)
                    print()
            except Exception as e:
                print(f"  [Metric] Result Accuracy: 0.00 ❌ (Expected SQL failed: {e})")
        else:
            print("  [Metric] Result Accuracy: 0.00 ❌ (Did not execute)")

        # 5. QUERY EQUIVALENCE — LLM-as-a-Judge (smarter prompt)
        # The judge is explicitly told to IGNORE cosmetic differences:
        # aliases, ORDER BY on same column, formatting, column naming.
        judge_prompt = dedent(f"""
        You are an expert SQL database administrator judging logical query equivalence.

        CRITICAL RULE: Two SQL queries are LOGICALLY EQUIVALENT if they produce the SAME SET of data
        rows for any possible database state. You MUST IGNORE these cosmetic differences:
          - Different or missing table aliases (e.g. "AS o" vs "o")
          - Different or missing column aliases (e.g. "AS total_qty" vs no alias)
          - Extra ORDER BY on the same column (ordering does NOT change the data SET returned)
          - Whitespace, newlines, and capitalization
          - JOIN direction (A JOIN B ON x=y is the same as B JOIN A ON y=x)

        However, these ARE real differences that make queries NOT equivalent:
          - A missing or extra table in a JOIN
          - Wrong aggregation column (e.g. COUNT(*) vs COUNT(order_id))
          - Missing GROUP BY
          - Different WHERE/HAVING conditions that filter different rows
          - LIMIT present in one but not the other (when it changes the result SET)

        Question: "{question}"

        Expected SQL:
        {expected_sql}

        Generated SQL:
        {generated_sql}

        Are these two queries logically equivalent (ignoring cosmetic differences listed above)?
        Reply with ONLY the single digit '1' for YES or '0' for NO. No explanation.
        """).strip()

        try:
            judge_response = llm.invoke(judge_prompt).content.strip()
            match = re.search(r'\b([01])\b', judge_response)
            equiv_score = float(match.group(1)) if match else 0.0
        except Exception as e:
            print(f"  [Error] LLM Judge failed: {e}")
            equiv_score = 0.0

        total_equivalence_accuracy += equiv_score
        icon = "✅" if equiv_score == 1.0 else "❌"
        print(f"  [Metric] Query Equivalence: {equiv_score:.2f} {icon} (LLM-as-a-Judge)")

        print()

    avg_exec_acc = total_execution_accuracy / total_questions
    avg_res_acc = total_result_accuracy / total_questions
    avg_equiv_acc = total_equivalence_accuracy / total_questions

    print(f"\n{'=' * 65}")
    print(f"  Text-to-SQL Evaluation Summary")
    print(f"{'=' * 65}")
    print(f"  Avg Execution Accuracy : {avg_exec_acc:.2f}")
    print(f"  Avg Result Accuracy    : {avg_res_acc:.2f}")
    print(f"  Avg Query Equivalence  : {avg_equiv_acc:.2f}")
    print(f"{'=' * 65}\n")

    return avg_exec_acc, avg_res_acc, avg_equiv_acc


if __name__ == "__main__":
    dataset_file = os.path.join(os.path.dirname(__file__), "eval_sql_dataset.json")
    evaluate_sql(dataset_file)
