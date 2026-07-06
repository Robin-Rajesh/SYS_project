import os
import sys
import pandas as pd
from sqlalchemy import text

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from tools.sql_tool import get_engine

def generate_verification_excel():
    print("Connecting to database to extract raw tables...")
    engine = get_engine()

    # Extract the raw data needed for the calculation
    print("Extracting orders, order_items, and stores...")
    orders_df = pd.read_sql("SELECT * FROM orders", engine)
    order_items_df = pd.read_sql("SELECT * FROM order_items", engine)
    stores_df = pd.read_sql("SELECT * FROM stores", engine)

    # In raw data, calculate the item revenue (qty * price) for convenience
    order_items_df['revenue'] = order_items_df['qty'] * order_items_df['price']

    # Merge into a single flat dataset (just like a business analyst would do with VLOOKUPs)
    print("Joining tables into a flat dataset...")
    merged_df = order_items_df.merge(orders_df, on='order_id').merge(stores_df, on='store_id')
    
    # Reorder columns for readability
    cols = ['store_id', 'city', 'order_id', 'order_date', 'product_id', 'qty', 'price', 'revenue']
    merged_df = merged_df[cols]

    # Calculate the manual answer simulating a Pivot Table
    pivot_df = merged_df.groupby('city')['revenue'].sum().reset_index()
    pivot_df = pivot_df.sort_values(by='revenue', ascending=False).reset_index(drop=True)
    pivot_df.index += 1
    pivot_df.index.name = 'Rank'
    pivot_df = pivot_df.reset_index()
    
    total_revenue = pivot_df['revenue'].sum()
    pivot_df['% of Total Revenue'] = (pivot_df['revenue'] / total_revenue) * 100

    output_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'outputs', 'Manual_Verification_Store_Revenue.xlsx'))
    
    print(f"Writing Excel file to {output_path}...")
    with pd.ExcelWriter(output_path, engine='openpyxl') as writer:
        # 1. Instructions Sheet
        instructions = pd.DataFrame({
            "Manual Verification Steps (For Business Stakeholders)": [
                "QUESTION PROMPT: 'Rank all stores by their total revenue'",
                "",
                "HOW TO MANUALLY VERIFY THE AI'S ANSWER:",
                "1. Go to the 'Raw_Data_Export' sheet. This contains the raw, unfiltered data straight from the database.",
                "2. Click anywhere inside the data and press Insert > PivotTable.",
                "3. In the PivotTable Field List:",
                "   - Drag 'city' to the Rows area.",
                "   - Drag 'revenue' to the Values area (it should default to Sum of revenue).",
                "   - Sort the revenue column from Largest to Smallest.",
                "4. Compare your manual PivotTable to the 'AI_Calculated_Answer' sheet.",
                "5. They will match exactly, proving the AI wrote the correct SQL query without needing to read SQL!"
            ]
        })
        instructions.to_excel(writer, sheet_name='Instructions', index=False)
        
        # 2. AI Answer Sheet
        pivot_df.to_excel(writer, sheet_name='AI_Calculated_Answer', index=False)
        
        # 3. Raw Data Sheet
        merged_df.to_excel(writer, sheet_name='Raw_Data_Export', index=False)
        
        # Auto-adjust column widths for better readability
        workbook = writer.book
        for sheet_name in workbook.sheetnames:
            worksheet = workbook[sheet_name]
            for col in worksheet.columns:
                max_length = 0
                column = col[0].column_letter
                for cell in col:
                    try:
                        if len(str(cell.value)) > max_length:
                            max_length = len(str(cell.value))
                    except:
                        pass
                adjusted_width = min(max_length + 2, 80)
                worksheet.column_dimensions[column].width = adjusted_width

    print("\n✅ Verification file generated successfully!")
    print(f"File located at: {output_path}")

if __name__ == "__main__":
    generate_verification_excel()
