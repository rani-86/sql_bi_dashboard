-- ============================================================
--  SQL BI DASHBOARD — QUERY LIBRARY
--  Rani Sharma | NIT Jamshedpur
--  Layers: Bronze → Silver → Gold
-- ============================================================


-- ============================================================
-- BRONZE LAYER: Raw data validation queries
-- ============================================================

-- B1: Record counts per table
SELECT 'customers'   AS tbl, COUNT(*) AS records FROM customers UNION ALL
SELECT 'products',          COUNT(*)             FROM products  UNION ALL
SELECT 'orders',            COUNT(*)             FROM orders    UNION ALL
SELECT 'order_items',       COUNT(*)             FROM order_items;

-- B2: Null check on critical columns
SELECT
    SUM(CASE WHEN customer_id IS NULL THEN 1 ELSE 0 END) AS null_customer_id,
    SUM(CASE WHEN email       IS NULL THEN 1 ELSE 0 END) AS null_email,
    SUM(CASE WHEN signup_date IS NULL THEN 1 ELSE 0 END) AS null_signup_date
FROM customers;

-- B3: Order status distribution
SELECT status, COUNT(*) AS cnt,
       ROUND(COUNT(*) * 100.0 / SUM(COUNT(*)) OVER(), 1) AS pct
FROM orders
GROUP BY status;


-- ============================================================
-- SILVER LAYER: Cleaned, joined, enriched views
-- ============================================================

-- S1: Enriched orders view (JOIN customers + orders + items + products)
-- Used as base for all Gold KPIs
SELECT
    o.order_id,
    o.order_date,
    o.status,
    o.payment_method,
    c.customer_id,
    c.name        AS customer_name,
    c.city,
    c.segment,
    p.category,
    p.product_name,
    oi.quantity,
    oi.unit_price,
    oi.discount,
    ROUND(oi.quantity * oi.unit_price * (1 - oi.discount), 2) AS line_revenue,
    ROUND(oi.quantity * (oi.unit_price - p.cost_price), 2)    AS line_profit
FROM orders o
JOIN customers   c  ON o.customer_id = c.customer_id
JOIN order_items oi ON o.order_id    = oi.order_id
JOIN products    p  ON oi.product_id = p.product_id
WHERE o.status = 'Completed';

-- S2: Monthly revenue aggregation (Silver → Gold prep)
WITH monthly AS (
    SELECT
        STRFTIME('%Y-%m', o.order_date) AS month,
        ROUND(SUM(oi.quantity * oi.unit_price * (1 - oi.discount)), 2) AS revenue
    FROM orders o
    JOIN order_items oi ON o.order_id = oi.order_id
    WHERE o.status = 'Completed'
    GROUP BY month
)
SELECT
    month,
    revenue,
    LAG(revenue) OVER (ORDER BY month)                    AS prev_month_revenue,
    ROUND((revenue - LAG(revenue) OVER (ORDER BY month))
          / LAG(revenue) OVER (ORDER BY month) * 100, 1) AS mom_growth_pct
FROM monthly
ORDER BY month;


-- ============================================================
-- GOLD LAYER: KPI Dashboards
-- ============================================================

-- ── REVENUE KPIs ──────────────────────────────────────────

-- G1: Total revenue, profit, orders, AOV
SELECT
    COUNT(DISTINCT o.order_id)                                          AS total_orders,
    ROUND(SUM(oi.quantity * oi.unit_price * (1-oi.discount)), 2)        AS total_revenue,
    ROUND(SUM(oi.quantity * (oi.unit_price - p.cost_price)), 2)         AS total_profit,
    ROUND(SUM(oi.quantity * oi.unit_price * (1-oi.discount))
          / COUNT(DISTINCT o.order_id), 2)                              AS avg_order_value
FROM orders o
JOIN order_items oi ON o.order_id    = oi.order_id
JOIN products    p  ON oi.product_id = p.product_id
WHERE o.status = 'Completed';

-- G2: Revenue by product category with profit margin
SELECT
    p.category,
    COUNT(DISTINCT o.order_id)                                       AS orders,
    ROUND(SUM(oi.quantity * oi.unit_price * (1-oi.discount)), 2)     AS revenue,
    ROUND(SUM(oi.quantity * (oi.unit_price - p.cost_price)), 2)      AS profit,
    ROUND(SUM(oi.quantity * (oi.unit_price - p.cost_price))
          / SUM(oi.quantity * oi.unit_price * (1-oi.discount)) * 100, 1) AS margin_pct
FROM orders o
JOIN order_items oi ON o.order_id    = oi.order_id
JOIN products    p  ON oi.product_id = p.product_id
WHERE o.status = 'Completed'
GROUP BY p.category
ORDER BY revenue DESC;

-- G3: Monthly revenue trend (Window Function)
SELECT
    STRFTIME('%Y-%m', o.order_date)                                   AS month,
    ROUND(SUM(oi.quantity * oi.unit_price * (1-oi.discount)), 2)      AS revenue,
    ROUND(AVG(SUM(oi.quantity * oi.unit_price * (1-oi.discount)))
          OVER (ORDER BY STRFTIME('%Y-%m', o.order_date)
                ROWS BETWEEN 2 PRECEDING AND CURRENT ROW), 2)         AS rolling_3m_avg,
    ROUND(SUM(SUM(oi.quantity * oi.unit_price * (1-oi.discount)))
          OVER (ORDER BY STRFTIME('%Y-%m', o.order_date)), 2)         AS cumulative_revenue
FROM orders o
JOIN order_items oi ON o.order_id = oi.order_id
WHERE o.status = 'Completed'
GROUP BY month
ORDER BY month;

-- G4: Top 10 products by revenue
SELECT
    p.product_name,
    p.category,
    SUM(oi.quantity)                                                  AS units_sold,
    ROUND(SUM(oi.quantity * oi.unit_price * (1-oi.discount)), 2)     AS revenue,
    RANK() OVER (ORDER BY SUM(oi.quantity * oi.unit_price * (1-oi.discount)) DESC) AS revenue_rank
FROM order_items oi
JOIN products p ON oi.product_id = p.product_id
JOIN orders   o ON oi.order_id   = o.order_id
WHERE o.status = 'Completed'
GROUP BY p.product_id
ORDER BY revenue_rank
LIMIT 10;


-- ── RETENTION KPIs ────────────────────────────────────────

-- G5: Monthly active customers + new vs returning
WITH first_orders AS (
    SELECT customer_id, MIN(order_date) AS first_order_date
    FROM orders WHERE status = 'Completed'
    GROUP BY customer_id
),
monthly_activity AS (
    SELECT
        STRFTIME('%Y-%m', o.order_date) AS month,
        o.customer_id,
        CASE WHEN STRFTIME('%Y-%m', o.order_date) = STRFTIME('%Y-%m', f.first_order_date)
             THEN 'New' ELSE 'Returning' END AS customer_type
    FROM orders o
    JOIN first_orders f ON o.customer_id = f.customer_id
    WHERE o.status = 'Completed'
    GROUP BY month, o.customer_id
)
SELECT
    month,
    COUNT(*) AS active_customers,
    SUM(CASE WHEN customer_type = 'New'       THEN 1 ELSE 0 END) AS new_customers,
    SUM(CASE WHEN customer_type = 'Returning' THEN 1 ELSE 0 END) AS returning_customers
FROM monthly_activity
GROUP BY month
ORDER BY month;

-- G6: Customer retention rate (month-over-month)
WITH monthly_customers AS (
    SELECT STRFTIME('%Y-%m', order_date) AS month, customer_id
    FROM orders WHERE status = 'Completed'
    GROUP BY month, customer_id
)
SELECT
    curr.month,
    COUNT(DISTINCT curr.customer_id)                      AS active_this_month,
    COUNT(DISTINCT prev.customer_id)                      AS retained_from_last_month,
    ROUND(COUNT(DISTINCT prev.customer_id) * 100.0
          / NULLIF(COUNT(DISTINCT curr.customer_id), 0), 1) AS retention_rate_pct
FROM monthly_customers curr
LEFT JOIN monthly_customers prev
    ON curr.customer_id = prev.customer_id
    AND prev.month = STRFTIME('%Y-%m',
        DATE(curr.month || '-01', '-1 month'))
GROUP BY curr.month
ORDER BY curr.month;

-- G7: Customer lifetime value (CLV) by segment
SELECT
    c.segment,
    COUNT(DISTINCT c.customer_id)                                     AS customers,
    ROUND(SUM(oi.quantity * oi.unit_price * (1-oi.discount))
          / COUNT(DISTINCT c.customer_id), 2)                         AS avg_clv,
    ROUND(COUNT(DISTINCT o.order_id) * 1.0
          / COUNT(DISTINCT c.customer_id), 1)                         AS avg_orders_per_customer
FROM customers c
JOIN orders      o  ON c.customer_id = o.customer_id
JOIN order_items oi ON o.order_id    = oi.order_id
WHERE o.status = 'Completed'
GROUP BY c.segment
ORDER BY avg_clv DESC;


-- ── COHORT ANALYSIS ───────────────────────────────────────

-- G8: Monthly cohort retention table
WITH cohorts AS (
    SELECT customer_id,
           STRFTIME('%Y-%m', MIN(order_date)) AS cohort_month
    FROM orders WHERE status = 'Completed'
    GROUP BY customer_id
),
cohort_activity AS (
    SELECT
        c.cohort_month,
        STRFTIME('%Y-%m', o.order_date) AS activity_month,
        COUNT(DISTINCT o.customer_id)   AS active_customers
    FROM cohorts c
    JOIN orders o ON c.customer_id = o.customer_id
    WHERE o.status = 'Completed'
    GROUP BY c.cohort_month, activity_month
),
cohort_sizes AS (
    SELECT cohort_month, COUNT(*) AS cohort_size
    FROM cohorts GROUP BY cohort_month
)
SELECT
    ca.cohort_month,
    cs.cohort_size,
    ca.activity_month,
    ca.active_customers,
    ROUND(ca.active_customers * 100.0 / cs.cohort_size, 1) AS retention_pct
FROM cohort_activity ca
JOIN cohort_sizes cs ON ca.cohort_month = cs.cohort_month
ORDER BY ca.cohort_month, ca.activity_month
LIMIT 100;


-- ── AUTOMATED REPORTING ───────────────────────────────────

-- G9: Weekly automated KPI summary (replaces manual Excel report)
WITH weekly AS (
    SELECT
        STRFTIME('%Y-W%W', o.order_date)                              AS week,
        COUNT(DISTINCT o.order_id)                                    AS orders,
        COUNT(DISTINCT o.customer_id)                                 AS unique_customers,
        ROUND(SUM(oi.quantity * oi.unit_price * (1-oi.discount)), 2) AS revenue,
        ROUND(AVG(oi.quantity * oi.unit_price * (1-oi.discount)), 2) AS avg_order_value
    FROM orders o
    JOIN order_items oi ON o.order_id = oi.order_id
    WHERE o.status = 'Completed'
    GROUP BY week
)
SELECT *,
    ROUND((revenue - LAG(revenue) OVER (ORDER BY week))
          / LAG(revenue) OVER (ORDER BY week) * 100, 1) AS wow_growth_pct
FROM weekly
ORDER BY week DESC
LIMIT 12;

-- G10: City-wise revenue leaderboard (Window Function — RANK)
SELECT
    c.city,
    COUNT(DISTINCT o.order_id)                                       AS orders,
    COUNT(DISTINCT c.customer_id)                                    AS customers,
    ROUND(SUM(oi.quantity * oi.unit_price * (1-oi.discount)), 2)    AS revenue,
    RANK() OVER (ORDER BY SUM(oi.quantity * oi.unit_price * (1-oi.discount)) DESC) AS city_rank
FROM customers c
JOIN orders      o  ON c.customer_id = o.customer_id
JOIN order_items oi ON o.order_id    = oi.order_id
WHERE o.status = 'Completed'
GROUP BY c.city
ORDER BY city_rank;
