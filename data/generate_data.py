"""
generate_data.py — Synthetic Sales Data & Policy Document Generator
====================================================================
This script creates:
  PART A — A SQLite database (sales.db) with 100,000 realistic sales rows.
  PART B — Three policy documents in the docs/ folder.

Run once before starting the agent:
    python data/generate_data.py
"""

import sqlite3
import random
import sys
from pathlib import Path
from datetime import datetime, timedelta
from faker import Faker

# ═══════════════════════════════════════════════════════════════
# PATH CONFIGURATION (matches config.py constants)
# ═══════════════════════════════════════════════════════════════

BASE_DIR = Path("C:/SEM5/SYS_project")
DATA_DIR = BASE_DIR / "data"
DOCS_DIR = BASE_DIR / "docs"
DB_PATH  = DATA_DIR / "sales.db"

# Ensure directories exist
DATA_DIR.mkdir(parents=True, exist_ok=True)
DOCS_DIR.mkdir(parents=True, exist_ok=True)

# Seed everything for reproducibility
SEED = 42
random.seed(SEED)
fake = Faker()
Faker.seed(SEED)

# ═══════════════════════════════════════════════════════════════
# PART A — SQLite Database Generation  (100,000 rows)
# ═══════════════════════════════════════════════════════════════

# ---------- Lookup Tables / Enumerations ----------

REGIONS = ["North", "South", "East", "West"]
STATES = {
    "North": ["New York", "Pennsylvania", "Connecticut", "Massachusetts", "New Jersey"],
    "South": ["Texas", "Florida", "Georgia", "Virginia", "North Carolina"],
    "East":  ["Ohio", "Michigan", "Illinois", "Indiana", "Wisconsin"],
    "West":  ["California", "Washington", "Oregon", "Colorado", "Arizona"],
}

CUSTOMER_SEGMENTS = ["Consumer", "Corporate", "Home Office"]

CATEGORIES = {
    "Technology":      ["Laptops", "Phones", "Tablets", "Monitors", "Printers",
                        "Accessories", "Software"],
    "Furniture":       ["Chairs", "Desks", "Bookcases", "Tables", "Filing Cabinets",
                        "Furnishings"],
    "Office Supplies": ["Paper", "Binders", "Pens", "Envelopes", "Labels",
                        "Staplers", "Storage"],
}

# Maps each sub-category to a realistic base-price range (min, max)
PRICE_RANGES = {
    "Laptops": (400, 2500), "Phones": (150, 1200), "Tablets": (200, 900),
    "Monitors": (120, 800), "Printers": (60, 500), "Accessories": (5, 150),
    "Software": (20, 500),
    "Chairs": (50, 700), "Desks": (80, 1200), "Bookcases": (60, 500),
    "Tables": (70, 900), "Filing Cabinets": (40, 300), "Furnishings": (10, 250),
    "Paper": (5, 50), "Binders": (3, 30), "Pens": (1, 20),
    "Envelopes": (2, 25), "Labels": (3, 15), "Staplers": (5, 40),
    "Storage": (10, 80),
}

DISCOUNT_TIERS = {
    "None": 0.00,
    "Bronze": 0.05,
    "Silver": 0.10,
    "Gold": 0.20,
    "Platinum": 0.30,
}

SHIP_MODES    = ["Standard", "Express", "Same Day", "First Class"]
PAYMENT_MODES = ["Credit Card", "Debit Card", "Cash", "Net Banking", "UPI"]

# Pre-generate a pool of sales rep names (50 reps)
SALES_REPS = [fake.name() for _ in range(50)]

# Date range: 2021-01-01 to 2024-12-31
START_DATE = datetime(2021, 1, 1)
END_DATE   = datetime(2024, 12, 31)
DATE_RANGE_DAYS = (END_DATE - START_DATE).days

# Total rows to generate
TOTAL_ROWS  = 100_000
BATCH_SIZE  = 1_000          # Insert in chunks for performance
RETURN_RATE = 0.05           # 5 % of orders are returned


def random_date():
    """Return a random date between START_DATE and END_DATE."""
    return START_DATE + timedelta(days=random.randint(0, DATE_RANGE_DAYS))


def generate_row(order_id: int) -> tuple:
    """Generate a single sales row as a tuple matching the schema."""

    # --- Customer ---
    customer_id   = f"CUST-{random.randint(1000, 9999)}"
    customer_name = fake.name()
    segment       = random.choice(CUSTOMER_SEGMENTS)

    # --- Dates ---
    order_date    = random_date()
    ship_lag      = random.randint(1, 14)          # 1–14 day shipping lag
    ship_date     = order_date + timedelta(days=ship_lag)
    ship_mode     = random.choice(SHIP_MODES)

    # --- Location ---
    region = random.choice(REGIONS)
    state  = random.choice(STATES[region])
    city   = fake.city()

    # --- Product ---
    category     = random.choice(list(CATEGORIES.keys()))
    sub_category = random.choice(CATEGORIES[category])
    product_id   = f"PROD-{random.randint(100, 999)}"
    product_name = f"{sub_category} - {fake.company_suffix()} {random.choice(['Pro', 'Elite', 'Basic', 'Plus', 'Ultra'])}"

    # --- Pricing ---
    price_lo, price_hi = PRICE_RANGES[sub_category]
    cost_price = round(random.uniform(price_lo, price_hi), 2)

    # Markup between 10 % and 80 %
    markup        = random.uniform(0.10, 0.80)
    selling_price = round(cost_price * (1 + markup), 2)

    # --- Discount ---
    tier     = random.choice(list(DISCOUNT_TIERS.keys()))
    discount = DISCOUNT_TIERS[tier]

    # --- Quantity & Financials ---
    quantity     = random.randint(1, 14)
    sales_amount = round(selling_price * quantity * (1 - discount), 2)
    cost_total   = round(cost_price * quantity, 2)

    # Introduce realistic negative profit on ~15 % of rows
    if random.random() < 0.15:
        profit = round(-random.uniform(1, cost_total * 0.3), 2)
    else:
        profit = round(sales_amount - cost_total, 2)

    profit_margin = round((profit / sales_amount) * 100, 2) if sales_amount else 0.0

    # --- Other ---
    payment_mode  = random.choice(PAYMENT_MODES)
    return_status = "Returned" if random.random() < RETURN_RATE else "Not Returned"
    sales_rep     = random.choice(SALES_REPS)

    return (
        f"ORD-{order_id:06d}",
        customer_id, customer_name, segment,
        order_date.strftime("%Y-%m-%d"),
        ship_date.strftime("%Y-%m-%d"),
        ship_mode, region, state, city,
        product_id, product_name, category, sub_category,
        sales_amount, quantity, discount, tier,
        profit, profit_margin, cost_price, selling_price,
        payment_mode, return_status, sales_rep,
    )


def create_database():
    """Create (or replace) the sales.db SQLite database with 100 K rows."""

    # Remove old database if it exists to start fresh
    if DB_PATH.exists():
        DB_PATH.unlink()
        print(f"[INFO] Removed old database: {DB_PATH}")

    conn = sqlite3.connect(str(DB_PATH))
    cur  = conn.cursor()

    # ---------- Create the sales table ----------
    cur.execute("""
        CREATE TABLE IF NOT EXISTS sales (
            Order_ID        TEXT PRIMARY KEY,
            Customer_ID     TEXT,
            Customer_Name   TEXT,
            Customer_Segment TEXT,
            Order_Date      TEXT,
            Ship_Date       TEXT,
            Ship_Mode       TEXT,
            Region          TEXT,
            State           TEXT,
            City            TEXT,
            Product_ID      TEXT,
            Product_Name    TEXT,
            Category        TEXT,
            Sub_Category    TEXT,
            Sales_Amount    REAL,
            Quantity        INTEGER,
            Discount        REAL,
            Discount_Tier   TEXT,
            Profit          REAL,
            Profit_Margin   REAL,
            Cost_Price      REAL,
            Selling_Price   REAL,
            Payment_Mode    TEXT,
            Return_Status   TEXT,
            Sales_Rep       TEXT
        );
    """)

    # ---------- Batch insert 100 K rows ----------
    insert_sql = """
        INSERT INTO sales VALUES (
            ?,?,?,?,?,?,?,?,?,?,
            ?,?,?,?,?,?,?,?,?,?,
            ?,?,?,?,?
        );
    """

    print(f"[INFO] Generating {TOTAL_ROWS:,} rows …")
    batch = []
    for i in range(1, TOTAL_ROWS + 1):
        batch.append(generate_row(i))

        if len(batch) >= BATCH_SIZE:
            cur.executemany(insert_sql, batch)
            batch.clear()

        if i % 10_000 == 0:
            print(f"  → {i:>7,} / {TOTAL_ROWS:,} rows generated")

    # Flush remaining rows
    if batch:
        cur.executemany(insert_sql, batch)

    conn.commit()
    conn.close()
    print(f"[DONE] Database saved to: {DB_PATH}")
    print(f"       Total rows: {TOTAL_ROWS:,}")


# ═══════════════════════════════════════════════════════════════
# PART B — Policy Document Generation
# ═══════════════════════════════════════════════════════════════

def create_policy_documents():
    """Write three policy .txt files to the docs/ directory."""

    # ---- 1. Sales Policy ----
    sales_policy = """\
═══════════════════════════════════════════════════════════════
                    SALES POLICY DOCUMENT
                    FY 2021 – FY 2024
═══════════════════════════════════════════════════════════════

1. QUARTERLY SALES TARGETS BY REGION (in USD)
───────────────────────────────────────────────
Region  |    Q1       |    Q2       |    Q3       |    Q4
--------|-------------|-------------|-------------|------------
North   | 2,500,000   | 3,000,000   | 3,200,000   | 4,000,000
South   | 2,000,000   | 2,500,000   | 2,800,000   | 3,500,000
East    | 1,800,000   | 2,200,000   | 2,500,000   | 3,200,000
West    | 2,200,000   | 2,700,000   | 3,000,000   | 3,800,000

2. DISCOUNT APPLICATION RULES
───────────────────────────────
- Discounts may only be applied via the approved Discount Tier system.
- Every discount above Bronze (5%) requires documented approval.
- No discount may exceed the Platinum tier (30%).
- Stacking of discount tiers on a single order is strictly prohibited.
- See the Discount Approval Matrix document for tier-specific rules.

3. RETURN POLICY
─────────────────
- Customers may request a return within 30 days of the Ship_Date.
- Returned items must be in original packaging and undamaged.
- Technology items (laptops, phones, tablets) have a 15-day return window.
- Returns are processed within 5 business days after receiving the item.
- Refunds are credited to the original payment method.
- Bulk orders (Quantity > 10) require regional manager approval for returns.
- Fraudulent returns are flagged and escalated to the compliance team.

4. SALES REP COMMISSION STRUCTURE
───────────────────────────────────
- Base commission: 3% of Sales_Amount for all confirmed (non-returned) orders.
- Bonus tiers:
    * Monthly sales > $50,000  → additional 1% bonus
    * Monthly sales > $100,000 → additional 2% bonus (total 5%)
    * Monthly sales > $200,000 → additional 3% bonus (total 6%)
- Commission on returned orders is clawed back in the following pay period.
- Platinum-tier discount orders receive 50% of the normal commission rate.

5. PERFORMANCE REVIEW TRIGGERS
────────────────────────────────
A performance review is automatically initiated if:
- A sales rep misses their quarterly target by more than 20%.
- Return rate for a rep exceeds 8% over a rolling 90-day window.
- Average discount offered by a rep exceeds 15% in any quarter.
- Three or more customer complaints are lodged in a single month.
- Compliance violations are reported by the internal audit team.

═══════════════════════════════════════════════════════════════
                         END OF DOCUMENT
═══════════════════════════════════════════════════════════════
"""

    # ---- 2. Discount Approval Matrix ----
    discount_matrix = """\
═══════════════════════════════════════════════════════════════
              DISCOUNT APPROVAL MATRIX
              Effective FY 2021 – FY 2024
═══════════════════════════════════════════════════════════════

1. DISCOUNT TIER DEFINITIONS & APPROVAL AUTHORITY
──────────────────────────────────────────────────

Tier       | Discount % | Approval Authority        | Max Units
-----------|------------|---------------------------|----------
None       |  0%        | No approval needed        | Unlimited
Bronze     |  5%        | Any Sales Rep             | Unlimited
Silver     | 10%        | Team Lead approval        | 50 units
Gold       | 20%        | Regional Manager approval | 25 units
Platinum   | 30%        | VP of Sales approval      | 10 units

2. SEASONAL / REGIONAL RESTRICTIONS
─────────────────────────────────────

Q3-SPECIFIC RULE (July – September):
  • The maximum allowed AVERAGE discount across all orders in the
    South region must not exceed 10%.
  • Individual Gold and Platinum orders are still permitted, but the
    aggregate average must remain at or below 10%.
  • Violations trigger an automatic audit of the responsible sales reps.

Q4-SPECIFIC RULE (October – December):
  • Platinum-tier discounts (30%) are FROZEN in the East region.
  • No new Platinum discount orders may be created in the East region
    during Q4 under any circumstances.
  • Existing Platinum orders placed before Q4 are honored.
  • This restriction is in place to protect Q4 margins for the
    fiscal year close.

3. VIOLATION ESCALATION PROCEDURE
───────────────────────────────────
Step 1: Automated alert is sent to the sales rep and their team lead.
Step 2: Team lead must respond within 24 hours with justification.
Step 3: If unjustified, the regional manager reviews the case within 48 hours.
Step 4: Confirmed violations are logged in the compliance database.
Step 5: Repeat violations (3+ in a quarter) trigger a formal PIP
         (Performance Improvement Plan).
Step 6: Egregious violations (willful override) result in immediate
         suspension of discount-granting privileges.

4. EXCEPTIONS
───────────────
- Government and educational institution orders may receive up to
  Gold-tier discounts without additional approval.
- Orders exceeding $500,000 in value may request a custom discount
  that must be approved by the Chief Revenue Officer (CRO).

═══════════════════════════════════════════════════════════════
                         END OF DOCUMENT
═══════════════════════════════════════════════════════════════
"""

    # ---- 3. Product Catalog ----
    product_catalog = """\
═══════════════════════════════════════════════════════════════
                     PRODUCT CATALOG
                     FY 2024 Edition
═══════════════════════════════════════════════════════════════

CATEGORY: TECHNOLOGY
─────────────────────
ID        | Product Name               | Base Price | Rec. Selling Price | Status
----------|----------------------------|-----------|-------------------|---------------
PROD-101  | UltraBook Pro 15           | $850.00   | $1,275.00         | Active
PROD-102  | UltraBook Air 13           | $650.00   | $975.00           | Active
PROD-103  | SmartPhone X200            | $400.00   | $699.00           | Active
PROD-104  | SmartPhone Lite S          | $180.00   | $299.00           | Active
PROD-105  | TabMax 10.5                | $320.00   | $499.00           | Active
PROD-106  | ClearView Monitor 27"      | $250.00   | $399.00           | Active
PROD-107  | LaserJet Pro Printer       | $180.00   | $299.00           | Discontinue Q2 2025
PROD-108  | Wireless Keyboard & Mouse  | $35.00    | $59.99            | Active
PROD-109  | CloudSync Software Suite   | $120.00   | $199.00           | Active

Profit Margin Target for Technology: 35% – 50%

CATEGORY: FURNITURE
─────────────────────
ID        | Product Name               | Base Price | Rec. Selling Price | Status
----------|----------------------------|-----------|-------------------|---------------
PROD-201  | ErgoComfort Executive Chair | $280.00   | $499.00           | Active
PROD-202  | StandUp Adjustable Desk    | $350.00   | $599.00           | Active
PROD-203  | ClassicWood Bookcase       | $150.00   | $249.00           | Active
PROD-204  | Conference Table 8-Seat    | $420.00   | $699.00           | Active
PROD-205  | Steel Filing Cabinet 4-Dr  | $90.00    | $159.00           | Active
PROD-206  | ModernLounge Sofa          | $500.00   | $849.00           | Discontinue Q3 2025
PROD-207  | WallMount Shelving Unit    | $65.00    | $109.00           | Active

Profit Margin Target for Furniture: 40% – 60%

CATEGORY: OFFICE SUPPLIES
─────────────────────────
ID        | Product Name               | Base Price | Rec. Selling Price | Status
----------|----------------------------|-----------|-------------------|---------------
PROD-301  | Premium Copy Paper (Ream)  | $4.50     | $8.99             | Active
PROD-302  | Heavy-Duty 3-Ring Binder   | $5.00     | $9.99             | Active
PROD-303  | Executive Pen Set          | $12.00    | $24.99            | Active
PROD-304  | Security Envelope Box      | $6.00     | $11.99            | Active
PROD-305  | Label Maker Pro            | $25.00    | $44.99            | Active
PROD-306  | Desktop Stapler Set        | $8.00     | $14.99            | Discontinue Q1 2025
PROD-307  | Modular Storage Bins       | $15.00    | $29.99            | Active

Profit Margin Target for Office Supplies: 50% – 100%

═══════════════════════════════════════════════════════════════
PRODUCTS FLAGGED FOR DISCONTINUATION
═══════════════════════════════════════════════════════════════
- PROD-107 (LaserJet Pro Printer)     → Discontinue by Q2 2025
  Reason: Declining demand, high support costs.
- PROD-206 (ModernLounge Sofa)        → Discontinue by Q3 2025
  Reason: Low margin, bulky shipping costs eating into profit.
- PROD-306 (Desktop Stapler Set)      → Discontinue by Q1 2025
  Reason: Commodity product, intense price competition.

Recommendation: Transition customers to alternative products and
offer a one-time 10% loyalty discount on replacement orders.

═══════════════════════════════════════════════════════════════
                         END OF DOCUMENT
═══════════════════════════════════════════════════════════════
"""

    # Write each document
    (DOCS_DIR / "sales_policy.txt").write_text(sales_policy, encoding="utf-8")
    print(f"[DONE] Created: {DOCS_DIR / 'sales_policy.txt'}")

    (DOCS_DIR / "discount_approval_matrix.txt").write_text(discount_matrix, encoding="utf-8")
    print(f"[DONE] Created: {DOCS_DIR / 'discount_approval_matrix.txt'}")

    (DOCS_DIR / "product_catalog.txt").write_text(product_catalog, encoding="utf-8")
    print(f"[DONE] Created: {DOCS_DIR / 'product_catalog.txt'}")


# ═══════════════════════════════════════════════════════════════
# MAIN ENTRY POINT
# ═══════════════════════════════════════════════════════════════

if __name__ == "__main__":
    print("=" * 60)
    print("  Agentic Sales Data Analyst — Data Generator")
    print("=" * 60)

    # Step 1: Generate the database
    create_database()

    # Step 2: Generate the policy documents
    print()
    create_policy_documents()

    print()
    print("=" * 60)
    print("  All data generated successfully!")
    print(f"  Database : {DB_PATH}")
    print(f"  Documents: {DOCS_DIR}")
    print("=" * 60)
