import sqlite3
import os
from pathlib import Path
from faker import Faker

# Paths
BASE_DIR = Path("C:/SEM5/SYS_project")
DATA_DIR = BASE_DIR / "data"
SALES_DB = DATA_DIR / "sales.db"
MASTER_DB = DATA_DIR / "master_data.db"

fake = Faker()

def generate_master_data():
    if not SALES_DB.exists():
        print(f"Error: {SALES_DB} not found. Run generate_data.py first.")
        return

    # Connect to sales.db to extract existing IDs
    sales_conn = sqlite3.connect(str(SALES_DB))
    sales_cur = sales_conn.cursor()

    print("Extracting unique customers and products from sales.db...")
    
    # Extract unique customers - only one row per ID
    # Use aggregation to pick the first name/segment for each ID
    sales_cur.execute("""
        SELECT Customer_ID, MIN(Customer_Name), MIN(Customer_Segment) 
        FROM sales 
        GROUP BY Customer_ID
    """)
    customers = sales_cur.fetchall()
    
    # Extract unique products - only one row per ID
    sales_cur.execute("""
        SELECT Product_ID, MIN(Product_Name), MIN(Category), MIN(Sub_Category) 
        FROM sales 
        GROUP BY Product_ID
    """)
    products = sales_cur.fetchall()
    
    sales_conn.close()

    # Create master_data.db
    if MASTER_DB.exists():
        MASTER_DB.unlink()
    
    master_conn = sqlite3.connect(str(MASTER_DB))
    master_cur = master_conn.cursor()

    # Create tables
    print("Creating tables in master_data.db...")
    master_cur.execute("""
        CREATE TABLE IF NOT EXISTS customers (
            customer_id TEXT PRIMARY KEY,
            name TEXT,
            segment TEXT,
            email TEXT,
            phone TEXT,
            address TEXT,
            loyalty_points INTEGER
        )
    """)

    master_cur.execute("""
        CREATE TABLE IF NOT EXISTS products (
            product_id TEXT PRIMARY KEY,
            name TEXT,
            category TEXT,
            sub_category TEXT,
            supplier TEXT,
            stock_level INTEGER,
            warranty_period TEXT
        )
    """)

    # Populate customers
    print(f"Populating {len(customers)} customers...")
    customer_rows = []
    for cid, cname, cseg in customers:
        customer_rows.append((
            cid, cname, cseg,
            fake.email(),
            fake.phone_number(),
            fake.address().replace("\n", ", "),
            fake.random_int(min=0, max=5000)
        ))
    
    master_cur.executemany("INSERT INTO customers VALUES (?, ?, ?, ?, ?, ?, ?)", customer_rows)

    # Populate products
    print(f"Populating {len(products)} products...")
    product_rows = []
    for pid, pname, pcat, psub in products:
        product_rows.append((
            pid, pname, pcat, psub,
            fake.company(),
            fake.random_int(min=10, max=1000),
            fake.random_element(elements=("1 Year", "2 Years", "3 Years", "5 Years", "Lifetime"))
        ))
    
    master_cur.executemany("INSERT INTO products VALUES (?, ?, ?, ?, ?, ?, ?)", product_rows)

    master_conn.commit()
    master_conn.close()
    print(f"Successfully created {MASTER_DB} with structured master tables.")

if __name__ == "__main__":
    generate_master_data()
