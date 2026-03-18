import sqlite3
import os
from pathlib import Path

# Path to the data directory
DATA_DIR = Path("C:/SEM5/SYS_project/data")
DATA_DIR.mkdir(parents=True, exist_ok=True)

db_path = DATA_DIR / "users.db"

# Sample User Data for the Star Schema
users_data = [
    (1, "Alice Johnson", "alice@example.com", "West"),
    (2, "Bob Smith", "bob@example.com", "East"),
    (3, "Charlie Davis", "charlie@example.com", "South"),
    (4, "Diana Prince", "diana@example.com", "Central"),
    (5, "Ethan Hunt", "ethan@example.com", "West"),
]

# Sample Employee Data
employees_data = [
    (101, "Alice Johnson", "Sales Manager"),
    (102, "Bob Smith", "Sales Associate"),
    (103, "Charlie Davis", "Senior Analyst"),
]

def create_users_db():
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # Create users table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY,
            name TEXT NOT NULL,
            email TEXT NOT NULL,
            region TEXT
        )
    """)

    # Create employees table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS employees (
            emp_id INTEGER PRIMARY KEY,
            name TEXT NOT NULL,
            role TEXT
        )
    """)

    # Insert data
    cursor.executemany("INSERT OR REPLACE INTO users VALUES (?, ?, ?, ?)", users_data)
    cursor.executemany("INSERT OR REPLACE INTO employees VALUES (?, ?, ?)", employees_data)

    conn.commit()
    conn.close()
    print(f"Database created at {db_path}")

if __name__ == "__main__":
    create_users_db()
