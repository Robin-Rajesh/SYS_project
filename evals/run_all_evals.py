import os
import sys

# Add project root to path so we can import project modules
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from evals.eval_retriever import evaluate_retrieval
from evals.eval_generator import evaluate_generation
from evals.eval_sql import evaluate_sql
from evals.eval_sql_structure import evaluate_sql_structure

def main():
    print("==================================================")
    print("       AI AGENT EVALUATION SUITE STARTING         ")
    print("==================================================\n")
    
    dataset_file = os.path.join(os.path.dirname(__file__), "eval_dataset.json")
    sql_dataset_file = os.path.join(os.path.dirname(__file__), "eval_sql_dataset.json")
    
    # 1. Evaluate Retrieval (Deterministic)
    precision, recall = evaluate_retrieval(dataset_file, k=4)
    
    print("\n--------------------------------------------------\n")
    
    # 2. Evaluate Generation (Hybrid: Deterministic + LLM Judge)
    overlap, relevance = evaluate_generation(dataset_file)

    print("\n--------------------------------------------------\n")
    
    # 3. Evaluate SQL Agent (Deterministic & Semantic)
    exec_acc, res_acc, equiv_acc = evaluate_sql(sql_dataset_file)
    
    print("\n--------------------------------------------------\n")
    
    # 4. Evaluate SQL Structural Correctness (Deep Query Analysis)
    structural_score = evaluate_sql_structure(sql_dataset_file)
    
    print("\n==================================================")
    print("                 FINAL REPORT                     ")
    print("==================================================")
    print(f"1. RAG RETRIEVAL (Deterministic Math)")
    print(f"   Precision@4 : {precision:.2f}")
    print(f"   Recall@4    : {recall:.2f}")
    print(f"   Status      : {'PASS' if recall >= 0.75 else 'NEEDS IMPROVEMENT'}")
    print()
    print(f"2. RAG GENERATION (Semantic Quality)")
    print(f"   Word Overlap: {overlap:.2f} (Deterministic)")
    print(f"   Relevance   : {relevance:.2f} (LLM-as-a-Judge)")
    print(f"   Status      : {'PASS' if relevance >= 0.80 else 'NEEDS IMPROVEMENT'}")
    print()
    print(f"3. TEXT-TO-SQL (Execution & Results — Deterministic)")
    print(f"   Exec Acc    : {exec_acc:.2f} (Did SQL run?)")
    print(f"   Result Acc  : {res_acc:.2f} (Did data match?)")
    print(f"   Equivalence : {equiv_acc:.2f} (LLM-as-a-Judge Syntax Match)")
    print(f"   Status      : {'PASS' if res_acc >= 0.80 else 'NEEDS IMPROVEMENT'}")
    print()
    print(f"4. SQL STRUCTURAL CORRECTNESS (Deep Query Analysis)")
    print(f"   Score       : {structural_score:.2f} ({structural_score:.0%}) (LLM-as-a-Judge)")
    print(f"   Dimensions  : Tables, Columns, JOINs, Aggregation, Filters")
    print(f"   Status      : {'PASS' if structural_score >= 0.80 else 'NEEDS IMPROVEMENT'}")
    print("==================================================\n")

if __name__ == "__main__":
    main()
