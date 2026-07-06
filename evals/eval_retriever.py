import sys
import os

# Ensure the root project directory is in the python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from tools.schema_retriever import retrieve_resolved_tables
import config

# Force IS_CLOUD to True so it actually uses Supabase pgvector
# (In local dev without this, it might just return all tables)
config.IS_CLOUD = True

TEST_CASES = [
    ("Which market performed best?", ['stores', 'orders', 'order_items']),
    ("Show refund rate by supplier", ['returns', 'suppliers', 'order_items']),
    ("Monthly revenue trend", ['orders', 'order_items']),
    ("Which employee sold the most items?", ['employees', 'orders', 'order_items']),
    ("What is our best selling product category?", ['categories', 'products', 'order_items']),
    ("How many packages are currently delayed?", ['shipments']),
    ("List customers who signed up but never bought anything", ['customers', 'orders']),
    ("Which promotion generated the highest sales?", ['promotions', 'orders', 'order_items']),
    ("What is the average payment amount per order?", ['payments', 'orders']),
    ("Find the top vendor by total units shipped", ['suppliers', 'products', 'order_items']),
    ("Are there regional differences in product returns?", ['returns', 'order_items', 'orders', 'stores']),
    ("Which city has the most active retail branches?", ['stores']),
    ("Identify items that were returned due to damage", ['returns', 'order_items', 'products']),
    ("Who is the manager of the top performing region?", ['employees', 'stores', 'orders']),
    ("Average order value during the summer sale", ['orders', 'order_items', 'promotions']),
    ("Do high-value orders have a higher refund rate?", ['returns', 'order_items', 'orders']),
    ("List the delivery status for all orders placed yesterday", ['shipments', 'orders']),
    ("Which customer demographics spend the most?", ['customers', 'orders', 'order_items']),
    ("Total inventory cost by supplier country", ['suppliers', 'products']),
    ("How many distinct brands do we carry?", ['products', 'categories']),
    # EDGE CASE: vague vocabulary
    ("What is our churn situation?", ['customers', 'orders']),
    # EDGE CASE: completely vague — dynamic threshold must NOT flood with all tables
    ("What do you think about our business?", []),
]

def run_eval():
    print("--- Starting Schema Retriever Evaluation ---\n")
    
    total_recall = 0.0
    total_precision = 0.0
    scored_tests = 0  # Only count tests with expected tables in aggregate
    
    for i, (question, expected) in enumerate(TEST_CASES, 1):
        print(f"Q{i}: {question}")
        print(f"  Expected: {expected}")
        
        try:
            retrieved = retrieve_resolved_tables(question)
        except Exception as e:
            print(f"  [ERROR] Call failed: {e}\n")
            continue
            
        retrieved_set = set(retrieved)
        expected_set = set(expected)
        
        # Special handling for vague/no-table-expected edge case
        if not expected_set:
            if len(retrieved_set) == 0:
                print(f"  [PASS] Correctly returned no tables\n")
            elif len(retrieved_set) <= 2:
                print(f"  [WARN] Returned {len(retrieved_set)} tables for vague query: {list(retrieved_set)} (marginal)\n")
            else:
                print(f"  [FAIL] DYNAMIC THRESHOLD FLOODED: returned {len(retrieved_set)} tables for completely vague question: {list(retrieved_set)}\n")
            continue
        
        # Recall: What % of the Expected tables did we actually retrieve?
        recall = len(retrieved_set & expected_set) / len(expected_set)
        
        # Precision: What % of the Retrieved tables were actually Expected?
        precision = len(retrieved_set & expected_set) / len(retrieved_set) if retrieved_set else 0.0
        
        missing = expected_set - retrieved_set
        extra = retrieved_set - expected_set
        
        total_recall += recall
        total_precision += precision
        scored_tests += 1
        
        status = "[PASS]" if recall == 1.0 else "[FAIL]"
        print(f"  {status} Recall: {recall:.0%} | Precision: {precision:.0%}")
        if missing:
            print(f"  [WARN] Missing tables: {list(missing)}")
        if extra:
            print(f"  [INFO] Extra tables: {list(extra)}")
        print()
        
    avg_recall = total_recall / scored_tests if scored_tests else 0
    avg_precision = total_precision / scored_tests if scored_tests else 0
    
    print("--- Final Results ---")
    print(f"Average Recall:    {avg_recall:.1%}  (target: >90%)")
    print(f"Average Precision: {avg_precision:.1%}  (target: >60%)")
    
    recall_pass = avg_recall >= 0.9
    precision_pass = avg_precision >= 0.6
    
    if recall_pass and precision_pass:
        print("\nSTATUS: PASS")
    else:
        failures = []
        if not recall_pass:
            failures.append(f"Recall {avg_recall:.1%} < 90%")
        if not precision_pass:
            failures.append(f"Precision {avg_precision:.1%} < 60%")
        print(f"\nSTATUS: FAIL ({', '.join(failures)})")

if __name__ == "__main__":
    run_eval()
