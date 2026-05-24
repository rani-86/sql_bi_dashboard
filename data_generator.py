"""
data_generator.py
Creates SQLite database and populates it with synthetic business data.
Simulates Bronze layer — raw transactional data.
Tables: customers, products, orders, order_items
"""

import sqlite3
import random
import numpy as np
from datetime import datetime, timedelta
import os

random.seed(42)
np.random.seed(42)

DB_PATH = "data/business.db"

# ── Schema (Bronze Layer — raw tables) ────────────────────────────────────
SCHEMA = """
CREATE TABLE IF NOT EXISTS customers (
    customer_id     INTEGER PRIMARY KEY,
    name            TEXT NOT NULL,
    email           TEXT UNIQUE,
    city            TEXT,
    country         TEXT,
    signup_date     TEXT,
    segment         TEXT   -- 'Consumer', 'Corporate', 'SMB'
);

CREATE TABLE IF NOT EXISTS products (
    product_id      INTEGER PRIMARY KEY,
    product_name    TEXT NOT NULL,
    category        TEXT,
    sub_category    TEXT,
    cost_price      REAL,
    sell_price      REAL
);

CREATE TABLE IF NOT EXISTS orders (
    order_id        INTEGER PRIMARY KEY,
    customer_id     INTEGER REFERENCES customers(customer_id),
    order_date      TEXT,
    ship_date       TEXT,
    status          TEXT,  -- 'Completed','Returned','Cancelled'
    payment_method  TEXT
);

CREATE TABLE IF NOT EXISTS order_items (
    item_id         INTEGER PRIMARY KEY,
    order_id        INTEGER REFERENCES orders(order_id),
    product_id      INTEGER REFERENCES products(product_id),
    quantity        INTEGER,
    unit_price      REAL,
    discount        REAL   -- 0.0 to 0.3
);
"""

# ── Sample data pools ──────────────────────────────────────────────────────
CITIES = ["Mumbai","Delhi","Bangalore","Chennai","Hyderabad",
          "Pune","Kolkata","Ahmedabad","Jaipur","Lucknow"]
SEGMENTS = ["Consumer","Corporate","SMB"]
CATEGORIES = {
    "Electronics":  ["Laptop","Phone","Tablet","Headphones","Camera"],
    "Clothing":     ["T-Shirt","Jeans","Jacket","Saree","Shoes"],
    "Grocery":      ["Rice","Oil","Sugar","Dal","Spices"],
    "Furniture":    ["Chair","Desk","Sofa","Bookshelf","Bed"],
    "Sports":       ["Cricket Bat","Football","Yoga Mat","Dumbbells","Cycle"],
}
PAYMENT_METHODS = ["Credit Card","Debit Card","UPI","NetBanking","Wallet"]
STATUS_WEIGHTS  = ["Completed"]*80 + ["Returned"]*12 + ["Cancelled"]*8


def generate_data(conn):
    cur = conn.cursor()
    cur.executescript(SCHEMA)

    # ── Customers (500) ───────────────────────────────────────────────────
    print("  Generating customers...")
    start = datetime(2022, 1, 1)
    for i in range(1, 501):
        signup = start + timedelta(days=random.randint(0, 900))
        cur.execute(
            "INSERT OR IGNORE INTO customers VALUES (?,?,?,?,?,?,?)",
            (i, f"Customer_{i:03d}",
             f"customer{i}@email.com",
             random.choice(CITIES), "India",
             signup.strftime("%Y-%m-%d"),
             random.choice(SEGMENTS))
        )

    # ── Products (60) ─────────────────────────────────────────────────────
    print("  Generating products...")
    pid = 1
    for cat, items in CATEGORIES.items():
        for item in items:
            for variant in range(1, 4):
                cost  = round(random.uniform(50, 800), 2)
                sell  = round(cost * random.uniform(1.2, 2.0), 2)
                cur.execute(
                    "INSERT OR IGNORE INTO products VALUES (?,?,?,?,?,?)",
                    (pid, f"{item} v{variant}", cat, item, cost, sell)
                )
                pid += 1

    # ── Orders + Items (20,000 orders) ────────────────────────────────────
    print("  Generating orders and order items...")
    order_id = 1
    item_id  = 1
    start    = datetime(2022, 1, 1)
    end      = datetime(2024, 12, 31)

    # Get all product ids
    cur.execute("SELECT product_id, sell_price FROM products")
    products = cur.fetchall()

    for _ in range(20000):
        cust_id    = random.randint(1, 500)
        order_date = start + timedelta(days=random.randint(0, (end-start).days))
        ship_date  = order_date + timedelta(days=random.randint(1, 7))
        status     = random.choice(STATUS_WEIGHTS)
        payment    = random.choice(PAYMENT_METHODS)

        cur.execute(
            "INSERT INTO orders VALUES (?,?,?,?,?,?)",
            (order_id, cust_id,
             order_date.strftime("%Y-%m-%d"),
             ship_date.strftime("%Y-%m-%d"),
             status, payment)
        )

        # 1–4 items per order
        n_items = random.randint(1, 4)
        chosen  = random.sample(products, min(n_items, len(products)))
        for prod_id, sell_price in chosen:
            qty      = random.randint(1, 5)
            discount = round(random.choice([0.0, 0.05, 0.10, 0.15, 0.20, 0.25]), 2)
            cur.execute(
                "INSERT INTO order_items VALUES (?,?,?,?,?,?)",
                (item_id, order_id, prod_id, qty,
                 round(sell_price, 2), discount)
            )
            item_id += 1

        order_id += 1

    conn.commit()
    print(f"  ✅ Inserted: 500 customers | {pid-1} products | {order_id-1} orders | {item_id-1} items")


def setup_database():
    os.makedirs("data", exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    generate_data(conn)
    conn.close()
    return DB_PATH


if __name__ == "__main__":
    setup_database()
    print(f"✅ Database ready → {DB_PATH}")
