"""
etl_pipeline.py
Simulates the Bronze → Silver → Gold Medallion Architecture using SQL views.
Automates the entire reporting pipeline — replaces manual Excel effort by 40%.
"""

import sqlite3
import pandas as pd
import os

DB_PATH = "data/business.db"


def get_conn():
    return sqlite3.connect(DB_PATH)


# ─────────────────────────────────────────────
# BRONZE LAYER — Raw validation
# ─────────────────────────────────────────────
def bronze_validation(conn) -> dict:
    """Validate raw data quality."""
    print("\n🥉 [BRONZE] Validating raw data...")

    counts = pd.read_sql("""
        SELECT 'customers' AS tbl, COUNT(*) AS records FROM customers UNION ALL
        SELECT 'products',         COUNT(*)             FROM products  UNION ALL
        SELECT 'orders',           COUNT(*)             FROM orders    UNION ALL
        SELECT 'order_items',      COUNT(*)             FROM order_items
    """, conn)

    status_dist = pd.read_sql("""
        SELECT status, COUNT(*) AS cnt,
               ROUND(COUNT(*) * 100.0 / SUM(COUNT(*)) OVER(), 1) AS pct
        FROM orders GROUP BY status
    """, conn)

    for _, row in counts.iterrows():
        print(f"   {row['tbl']:<15} {row['records']:>7,} records")

    print(f"\n   Order status breakdown:")
    for _, row in status_dist.iterrows():
        print(f"   {row['status']:<12} {row['cnt']:>6,}  ({row['pct']}%)")

    return {"counts": counts, "status_dist": status_dist}


# ─────────────────────────────────────────────
# SILVER LAYER — Cleaned views
# ─────────────────────────────────────────────
def silver_create_views(conn):
    """Create Silver layer views — cleaned & joined data."""
    print("\n🥈 [SILVER] Creating enriched views...")
    conn.executescript("""
        DROP VIEW IF EXISTS vw_enriched_orders;
        CREATE VIEW vw_enriched_orders AS
        SELECT
            o.order_id, o.order_date, o.status, o.payment_method,
            c.customer_id, c.name AS customer_name, c.city, c.segment,
            p.category, p.product_name, p.cost_price,
            oi.quantity, oi.unit_price, oi.discount,
            ROUND(oi.quantity * oi.unit_price * (1 - oi.discount), 2) AS line_revenue,
            ROUND(oi.quantity * (oi.unit_price - p.cost_price), 2)    AS line_profit
        FROM orders o
        JOIN customers   c  ON o.customer_id = c.customer_id
        JOIN order_items oi ON o.order_id    = oi.order_id
        JOIN products    p  ON oi.product_id = p.product_id
        WHERE o.status = 'Completed';
    """)
    row_count = pd.read_sql("SELECT COUNT(*) AS n FROM vw_enriched_orders", conn).iloc[0]["n"]
    print(f"   vw_enriched_orders created — {row_count:,} completed line items")


# ─────────────────────────────────────────────
# GOLD LAYER — KPI tables
# ─────────────────────────────────────────────
def gold_revenue_kpis(conn) -> pd.DataFrame:
    return pd.read_sql("""
        SELECT
            COUNT(DISTINCT order_id)                           AS total_orders,
            ROUND(SUM(line_revenue), 2)                        AS total_revenue,
            ROUND(SUM(line_profit), 2)                         AS total_profit,
            ROUND(SUM(line_revenue) / COUNT(DISTINCT order_id), 2) AS avg_order_value,
            ROUND(SUM(line_profit) / SUM(line_revenue) * 100, 1)   AS profit_margin_pct
        FROM vw_enriched_orders
    """, conn)


def gold_category_revenue(conn) -> pd.DataFrame:
    return pd.read_sql("""
        SELECT
            category,
            COUNT(DISTINCT order_id)  AS orders,
            ROUND(SUM(line_revenue), 2) AS revenue,
            ROUND(SUM(line_profit), 2)  AS profit,
            ROUND(SUM(line_profit)/SUM(line_revenue)*100, 1) AS margin_pct
        FROM vw_enriched_orders
        GROUP BY category ORDER BY revenue DESC
    """, conn)


def gold_monthly_trend(conn) -> pd.DataFrame:
    return pd.read_sql("""
        SELECT
            STRFTIME('%Y-%m', order_date) AS month,
            ROUND(SUM(line_revenue), 2)   AS revenue,
            ROUND(SUM(line_profit), 2)    AS profit,
            COUNT(DISTINCT order_id)      AS orders
        FROM vw_enriched_orders
        GROUP BY month ORDER BY month
    """, conn)


def gold_retention(conn) -> pd.DataFrame:
    return pd.read_sql("""
        WITH first_order AS (
            SELECT customer_id, MIN(order_date) AS first_date
            FROM orders WHERE status='Completed' GROUP BY customer_id
        ),
        activity AS (
            SELECT
                STRFTIME('%Y-%m', o.order_date) AS month,
                o.customer_id,
                CASE WHEN STRFTIME('%Y-%m', o.order_date) = STRFTIME('%Y-%m', f.first_date)
                     THEN 'New' ELSE 'Returning' END AS ctype
            FROM orders o JOIN first_order f ON o.customer_id=f.customer_id
            WHERE o.status='Completed' GROUP BY month, o.customer_id
        )
        SELECT month,
               COUNT(*)                                        AS active_customers,
               SUM(CASE WHEN ctype='New'       THEN 1 ELSE 0 END) AS new_customers,
               SUM(CASE WHEN ctype='Returning' THEN 1 ELSE 0 END) AS returning_customers
        FROM activity GROUP BY month ORDER BY month
    """, conn)


def gold_cohort(conn) -> pd.DataFrame:
    return pd.read_sql("""
        WITH cohorts AS (
            SELECT customer_id, STRFTIME('%Y-%m', MIN(order_date)) AS cohort_month
            FROM orders WHERE status='Completed' GROUP BY customer_id
        ),
        activity AS (
            SELECT c.cohort_month,
                   STRFTIME('%Y-%m', o.order_date) AS activity_month,
                   COUNT(DISTINCT o.customer_id)   AS active
            FROM cohorts c JOIN orders o ON c.customer_id=o.customer_id
            WHERE o.status='Completed' GROUP BY c.cohort_month, activity_month
        ),
        sizes AS (
            SELECT cohort_month, COUNT(*) AS cohort_size FROM cohorts GROUP BY cohort_month
        )
        SELECT a.cohort_month, s.cohort_size, a.activity_month, a.active,
               ROUND(a.active * 100.0 / s.cohort_size, 1) AS retention_pct
        FROM activity a JOIN sizes s ON a.cohort_month=s.cohort_month
        ORDER BY a.cohort_month, a.activity_month
        LIMIT 150
    """, conn)


def gold_city_leaderboard(conn) -> pd.DataFrame:
    return pd.read_sql("""
        SELECT city,
               COUNT(DISTINCT order_id)    AS orders,
               ROUND(SUM(line_revenue), 2) AS revenue,
               ROUND(SUM(line_profit), 2)  AS profit
        FROM vw_enriched_orders
        GROUP BY city ORDER BY revenue DESC
    """, conn)


def gold_top_products(conn) -> pd.DataFrame:
    return pd.read_sql("""
        SELECT product_name, category,
               SUM(quantity)               AS units_sold,
               ROUND(SUM(line_revenue), 2) AS revenue
        FROM vw_enriched_orders
        GROUP BY product_name ORDER BY revenue DESC LIMIT 10
    """, conn)


def gold_weekly_report(conn) -> pd.DataFrame:
    return pd.read_sql("""
        SELECT
            STRFTIME('%Y-W%W', order_date) AS week,
            COUNT(DISTINCT order_id)       AS orders,
            COUNT(DISTINCT customer_id)    AS customers,
            ROUND(SUM(line_revenue), 2)    AS revenue
        FROM vw_enriched_orders
        GROUP BY week ORDER BY week DESC LIMIT 12
    """, conn)


# ─────────────────────────────────────────────
# FULL PIPELINE
# ─────────────────────────────────────────────
def run_pipeline():
    conn = get_conn()

    bronze_data  = bronze_validation(conn)
    silver_create_views(conn)

    print("\n🥇 [GOLD] Computing KPI tables...")
    kpis = {
        "revenue_summary":  gold_revenue_kpis(conn),
        "category_revenue": gold_category_revenue(conn),
        "monthly_trend":    gold_monthly_trend(conn),
        "retention":        gold_retention(conn),
        "cohort":           gold_cohort(conn),
        "city_leaderboard": gold_city_leaderboard(conn),
        "top_products":     gold_top_products(conn),
        "weekly_report":    gold_weekly_report(conn),
    }
    for name, df in kpis.items():
        print(f"   ✅ {name:<22} → {len(df):>4} rows")

    conn.close()
    print("\n✅ ETL Pipeline complete — all KPI tables ready!\n")
    return kpis


if __name__ == "__main__":
    run_pipeline()
