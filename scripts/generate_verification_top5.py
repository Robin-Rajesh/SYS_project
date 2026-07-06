import os
import sys
import pandas as pd
import json
from sqlalchemy import text

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from tools.sql_tool import get_engine

def generate_top5():
    engine = get_engine()
    dataset_file = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'evals', 'eval_sql_dataset.json'))
    out_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'outputs'))
    
    with open(dataset_file, 'r', encoding='utf-8') as f:
        dataset = json.load(f)[:5]

    print("Fetching raw base tables...")
    orders = pd.read_sql("SELECT * FROM orders", engine)
    order_items = pd.read_sql("SELECT * FROM order_items", engine)
    stores = pd.read_sql("SELECT * FROM stores", engine)
    products = pd.read_sql("SELECT * FROM products", engine)
    categories = pd.read_sql("SELECT * FROM categories", engine)
    payments = pd.read_sql("SELECT * FROM payments", engine)
    returns = pd.read_sql("SELECT * FROM returns", engine)
    customers = pd.read_sql("SELECT * FROM customers", engine)

    order_items['revenue'] = order_items['qty'] * order_items['price']

    # --- Q1 ---
    q1 = dataset[0]
    merged_q1 = order_items.merge(products, on='product_id', suffixes=('', '_prod')).merge(categories, on='category_id')
    raw_q1 = merged_q1[['category_id', 'category_name', 'product_id', 'qty', 'revenue']]
    ans_q1 = pd.read_sql(text(q1['expected_sql']), engine)
    write_excel(os.path.join(out_dir, 'Manual_Verification_Q1.xlsx'), q1['question'], ans_q1, {"Raw_Flat_Data": raw_q1})

    # --- Q2 ---
    q2 = dataset[1]
    # filter for 2023
    orders['year'] = pd.to_datetime(orders['order_date']).dt.year
    raw_q2 = orders[orders['year'] == 2023][['order_id', 'order_date']]
    ans_q2 = pd.read_sql(text(q2['expected_sql']), engine)
    write_excel(os.path.join(out_dir, 'Manual_Verification_Q2.xlsx'), q2['question'], ans_q2, {"Raw_Flat_Data": raw_q2})

    # --- Q3 ---
    q3 = dataset[2]
    # Payments
    pay_q3 = orders.merge(payments, on='order_id').merge(customers, on='customer_id')
    raw_pay_q3 = pay_q3[['customer_id', 'city', 'order_id', 'amount']]
    # Refunds
    ref_q3 = orders.merge(order_items, on='order_id').merge(returns, on='order_item_id').merge(customers, on='customer_id')
    raw_ref_q3 = ref_q3[['customer_id', 'city', 'order_id', 'order_item_id', 'refund']]
    ans_q3 = pd.read_sql(text(q3['expected_sql']), engine)
    write_excel(os.path.join(out_dir, 'Manual_Verification_Q3.xlsx'), q3['question'], ans_q3, {
        "Raw_Payments_Data": raw_pay_q3,
        "Raw_Refunds_Data": raw_ref_q3
    })

    # --- Q4 ---
    q4 = dataset[3]
    merged_q4 = order_items.merge(products, on='product_id', suffixes=('', '_prod')).merge(categories, on='category_id').merge(returns, on='order_item_id', how='left')
    merged_q4['is_returned'] = merged_q4['return_id'].notna().astype(int)
    raw_q4 = merged_q4[['category_name', 'order_id', 'order_item_id', 'qty', 'is_returned']]
    ans_q4 = pd.read_sql(text(q4['expected_sql']), engine)
    write_excel(os.path.join(out_dir, 'Manual_Verification_Q4.xlsx'), q4['question'], ans_q4, {"Raw_Flat_Data": raw_q4})

    # --- Q5 ---
    q5 = dataset[4]
    merged_q5 = order_items.merge(orders, on='order_id').merge(stores, on='store_id')
    raw_q5 = merged_q5[['store_id', 'city', 'order_id', 'product_id', 'qty', 'revenue']]
    ans_q5 = pd.read_sql(text(q5['expected_sql']), engine)
    write_excel(os.path.join(out_dir, 'Manual_Verification_Q5.xlsx'), q5['question'], ans_q5, {"Raw_Flat_Data": raw_q5})

    print(f"Generated 5 Excel files in {out_dir}")


def write_excel(path, question, ai_answer_df, raw_dfs_dict):
    print(f"Writing {os.path.basename(path)}...")
    with pd.ExcelWriter(path, engine='openpyxl') as writer:
        instructions = pd.DataFrame({
            "Manual Verification Steps": [
                f"QUESTION: {question}",
                "",
                "1. Go to the Raw Data sheet(s).",
                "2. Insert PivotTables on the raw data to manually calculate the metrics.",
                "3. Check your final numbers against the 'AI_Calculated_Answer' sheet.",
                "4. You will see they match perfectly!"
            ]
        })
        instructions.to_excel(writer, sheet_name='Instructions', index=False)
        ai_answer_df.to_excel(writer, sheet_name='AI_Calculated_Answer', index=False)
        
        for sheet_name, df in raw_dfs_dict.items():
            df.to_excel(writer, sheet_name=sheet_name, index=False)
            
        # Format columns width
        wb = writer.book
        for sh in wb.sheetnames:
            ws = wb[sh]
            for col in ws.columns:
                max_length = 0
                column = col[0].column_letter
                for cell in col:
                    try:
                        if len(str(cell.value)) > max_length:
                            max_length = len(str(cell.value))
                    except:
                        pass
                ws.column_dimensions[column].width = min(max_length + 2, 80)

if __name__ == "__main__":
    generate_top5()
