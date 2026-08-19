"""
data_generator.py
Creates SQLite database and populates it with synthetic business data.
Simulates Bronze layer — raw transactional data.
Tables: customers, products, orders, order_items

Data is generated with deliberate real-world skew instead of uniform
randomness — city/segment population weights, category-specific pricing,
a popularity long-tail on products, and per-customer loyalty tiers that
drive realistic churn/retention curves instead of everyone ordering in
every month by statistical coincidence.
"""

import sqlite3
import numpy as np
from datetime import datetime, timedelta
import os

rng = np.random.default_rng(42)

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

-- Audit trail for order status changes. Orders are inserted as 'Processing'
-- and then moved to their final status (Completed/Returned/Cancelled) via
-- an UPDATE, which is what actually fires this trigger — it isn't just
-- decorative DDL, every order in the dataset produces one audit row.
CREATE TABLE IF NOT EXISTS order_audit_log (
    audit_id        INTEGER PRIMARY KEY AUTOINCREMENT,
    order_id        INTEGER REFERENCES orders(order_id),
    old_status      TEXT,
    new_status      TEXT,
    changed_at      TEXT DEFAULT CURRENT_TIMESTAMP
);

DROP TRIGGER IF EXISTS trg_log_order_status_change;
CREATE TRIGGER trg_log_order_status_change
AFTER UPDATE OF status ON orders
FOR EACH ROW
WHEN OLD.status IS NOT NEW.status
BEGIN
    INSERT INTO order_audit_log (order_id, old_status, new_status)
    VALUES (NEW.order_id, OLD.status, NEW.status);
END;
"""

# ── Sample data pools ──────────────────────────────────────────────────────
# City weights loosely follow relative metro population/order-volume skew —
# Mumbai/Delhi/Bangalore should dominate revenue, small cities trail behind.
CITIES = ["Mumbai","Delhi","Bangalore","Chennai","Hyderabad",
          "Pune","Kolkata","Ahmedabad","Jaipur","Lucknow"]
CITY_WEIGHTS = np.array([19, 16, 14, 9, 9, 8, 7, 6, 6, 6], dtype=float)
CITY_WEIGHTS /= CITY_WEIGHTS.sum()

# Consumer dominates by customer count; Corporate is rare but high-value.
SEGMENTS = ["Consumer", "Corporate", "SMB"]
SEGMENT_WEIGHTS = np.array([0.62, 0.10, 0.28])

# Each category gets its own price range, margin range, and share of order
# volume — Grocery/Clothing are frequent+cheap, Electronics/Furniture are
# rare+expensive, so category revenue mixes stop looking like copies of
# each other.
CATEGORIES = {
    "Electronics": {"items": ["Laptop","Phone","Tablet","Headphones","Camera"],
                     "cost_range": (300, 1600), "margin_range": (1.15, 1.35), "order_share": 0.14},
    "Clothing":    {"items": ["T-Shirt","Jeans","Jacket","Saree","Shoes"],
                     "cost_range": (15, 150),   "margin_range": (1.4, 2.3),  "order_share": 0.30},
    "Grocery":     {"items": ["Rice","Oil","Sugar","Dal","Spices"],
                     "cost_range": (5, 60),     "margin_range": (1.1, 1.3),  "order_share": 0.32},
    "Furniture":   {"items": ["Chair","Desk","Sofa","Bookshelf","Bed"],
                     "cost_range": (200, 2200), "margin_range": (1.2, 1.5),  "order_share": 0.08},
    "Sports":      {"items": ["Cricket Bat","Football","Yoga Mat","Dumbbells","Cycle"],
                     "cost_range": (30, 320),   "margin_range": (1.3, 1.9),  "order_share": 0.16},
}

PAYMENT_METHODS = ["UPI", "Credit Card", "Debit Card", "NetBanking", "Wallet"]
PAYMENT_WEIGHTS = np.array([0.45, 0.22, 0.14, 0.11, 0.08])  # UPI dominance is realistic for India

STATUSES = ["Completed", "Returned", "Cancelled"]
STATUS_WEIGHTS = np.array([0.80, 0.12, 0.08])

DISCOUNTS = [0.0, 0.0, 0.0, 0.05, 0.10, 0.15, 0.20, 0.25]  # most orders get no discount

# Customer loyalty tiers — this is what actually drives realistic retention:
# a minority of loyal repeat buyers, a larger occasional-buyer middle, and a
# sizeable one-time-purchase group that never comes back. Real e-commerce
# retention curves decay because most customers ARE one-time buyers, not
# because of a bug — this models that directly instead of letting every
# customer order in nearly every month by uniform-random coincidence.
TIERS = ["Loyal", "Occasional", "OneTime"]
TIER_WEIGHTS = np.array([0.15, 0.45, 0.40])
TIER_PARAMS = {
    "Loyal":      {"gap_mean_days": 22, "gap_sigma": 0.5, "n_orders_range": (15, 60)},
    "Occasional": {"gap_mean_days": 55, "gap_sigma": 0.6, "n_orders_range": (3, 18)},
    "OneTime":    {"gap_mean_days": None, "n_orders_range": (1, 1)},
}

N_CUSTOMERS = 1800  # scaled up so total order volume lands near the original ~20K orders

START = datetime(2022, 1, 1)
END = datetime(2024, 12, 31)
TOTAL_DAYS = (END - START).days


def generate_data(conn):
    cur = conn.cursor()
    cur.executescript(SCHEMA)

    # ── Customers ──────────────────────────────────────────────────────────
    print("  Generating customers...")
    customer_tiers = {}
    for i in range(1, N_CUSTOMERS + 1):
        # Spread signups across nearly the entire window (not just the
        # first 900 of ~1095 days) — otherwise acquisition effectively
        # stops 6 months before the data ends, which makes the final
        # months' "active customers" almost entirely returning by
        # definition rather than reflecting real retention behavior.
        signup = START + timedelta(days=int(rng.integers(0, TOTAL_DAYS - 30)))
        city = rng.choice(CITIES, p=CITY_WEIGHTS)
        segment = rng.choice(SEGMENTS, p=SEGMENT_WEIGHTS)
        tier = rng.choice(TIERS, p=TIER_WEIGHTS)
        customer_tiers[i] = (tier, signup)

        cur.execute(
            "INSERT OR IGNORE INTO customers VALUES (?,?,?,?,?,?,?)",
            (i, f"Customer_{i:03d}",
             f"customer{i}@email.com",
             city, "India",
             signup.strftime("%Y-%m-%d"),
             segment)
        )

    # ── Products (75) ─────────────────────────────────────────────────────
    print("  Generating products...")
    pid = 1
    product_category = {}
    product_popularity = {}
    for cat, spec in CATEGORIES.items():
        cost_lo, cost_hi = spec["cost_range"]
        margin_lo, margin_hi = spec["margin_range"]
        for item in spec["items"]:
            for variant in range(1, 4):
                cost = round(float(rng.uniform(cost_lo, cost_hi)), 2)
                sell = round(cost * float(rng.uniform(margin_lo, margin_hi)), 2)
                cur.execute(
                    "INSERT OR IGNORE INTO products VALUES (?,?,?,?,?,?)",
                    (pid, f"{item} v{variant}", cat, item, cost, sell)
                )
                # Long-tail popularity within a category — a couple of
                # products per category sell far more than the rest,
                # so "Top Products" charts stop being a flat staircase.
                product_category[pid] = cat
                product_popularity[pid] = float(rng.lognormal(mean=0.0, sigma=0.9))
                pid += 1

    cur.execute("SELECT product_id, sell_price FROM products")
    products = {row[0]: row[1] for row in cur.fetchall()}

    # Precompute per-category product pools with normalized popularity weights
    category_products = {cat: [] for cat in CATEGORIES}
    for p_id, cat in product_category.items():
        category_products[cat].append(p_id)

    category_names = list(CATEGORIES.keys())
    category_order_weights = np.array([CATEGORIES[c]["order_share"] for c in category_names])
    category_order_weights /= category_order_weights.sum()

    def pick_product():
        cat = rng.choice(category_names, p=category_order_weights)
        pool = category_products[cat]
        weights = np.array([product_popularity[p] for p in pool])
        weights /= weights.sum()
        return rng.choice(pool, p=weights)

    # ── Orders + Items ─────────────────────────────────────────────────────
    # Each customer's order dates are generated from their own loyalty tier
    # instead of one global uniform draw — this is what produces realistic,
    # decaying cohort retention and a genuine new-vs-returning split instead
    # of near-100% retention by statistical coincidence.
    print("  Generating orders and order items (per-customer tier-based activity)...")
    order_id = 1
    item_id = 1

    for cust_id in range(1, N_CUSTOMERS + 1):
        tier, signup = customer_tiers[cust_id]
        params = TIER_PARAMS[tier]
        lo, hi = params["n_orders_range"]
        n_orders = int(rng.integers(lo, hi + 1))

        days_since_signup_max = (END - signup).days
        if days_since_signup_max <= 0:
            continue

        first_gap = int(rng.integers(0, min(45, max(1, days_since_signup_max))))
        current_date = signup + timedelta(days=first_gap)

        for _ in range(n_orders):
            if current_date > END:
                break

            final_status = rng.choice(STATUSES, p=STATUS_WEIGHTS)
            payment = rng.choice(PAYMENT_METHODS, p=PAYMENT_WEIGHTS)
            ship_date = current_date + timedelta(days=int(rng.integers(1, 8)))

            # Insert as 'Processing', then move to the final status via
            # UPDATE — this fires trg_log_order_status_change and gives
            # every order a real row in order_audit_log.
            cur.execute(
                "INSERT INTO orders VALUES (?,?,?,?,?,?)",
                (order_id, cust_id,
                 current_date.strftime("%Y-%m-%d"),
                 ship_date.strftime("%Y-%m-%d"),
                 "Processing", payment)
            )
            cur.execute(
                "UPDATE orders SET status = ? WHERE order_id = ?",
                (final_status, order_id)
            )

            n_items = int(rng.integers(1, 5))
            for _ in range(n_items):
                prod_id = pick_product()
                sell_price = products[prod_id]
                qty = int(rng.choice([1, 2, 3, 4, 5], p=[0.45, 0.25, 0.15, 0.10, 0.05]))
                discount = float(rng.choice(DISCOUNTS))
                cur.execute(
                    "INSERT INTO order_items VALUES (?,?,?,?,?,?)",
                    (item_id, order_id, int(prod_id), qty,
                     round(sell_price, 2), discount)
                )
                item_id += 1

            order_id += 1

            # Advance to next order date using a lognormal gap so most
            # repeat purchases come soon-ish but a long tail comes back
            # much later — real repeat-purchase gaps aren't symmetric.
            gap_mean = params["gap_mean_days"]
            if gap_mean is None:  # OneTime tier never reorders
                break
            gap_days = float(rng.lognormal(mean=np.log(gap_mean), sigma=params["gap_sigma"]))
            current_date = current_date + timedelta(days=max(3, round(gap_days)))

    conn.commit()
    print(f"  ✅ Inserted: {N_CUSTOMERS} customers | {pid-1} products | {order_id-1} orders | {item_id-1} items")


def setup_database():
    os.makedirs("data", exist_ok=True)
    if os.path.exists(DB_PATH):
        os.remove(DB_PATH)  # avoid duplicate rows from re-running on a stale DB
    conn = sqlite3.connect(DB_PATH)
    generate_data(conn)
    conn.close()
    return DB_PATH


if __name__ == "__main__":
    setup_database()
    print(f"✅ Database ready → {DB_PATH}")
