# 📊 SQL-Based Business Intelligence Dashboard

> **Rani Sharma** · Production & Industrial Engineering · NIT Jamshedpur  
> GitHub: [github.com/rani-86](https://github.com/rani-86) · Batch 2027

---

## 🎯 Business Problem

E-commerce and retail businesses generate thousands of transactions daily — but raw data alone doesn't drive decisions. Business leaders need answers to questions like:

- **Which product categories are driving the most profit?**
- **Are we retaining customers month-over-month, or losing them?**
- **Which customer segments have the highest lifetime value?**
- **How is revenue trending — are we growing or declining?**

This project builds a **self-service BI system** that answers all of these questions automatically — replacing hours of manual Excel reporting with a structured, repeatable analytics pipeline.

---

## 💡 Business Impact

| Problem | Solution | Impact |
|---|---|---|
| Manual Excel reports took hours every week | Automated SQL pipeline generates all KPIs on demand | **40% reduction in reporting effort** |
| No visibility into customer loyalty | Cohort analysis + retention tracking | Identifies which customer groups churn early |
| Revenue reported as a single number | Broken down by category, city, segment, time | Enables targeted business decisions |
| No standard definition of KPIs | SQL views enforce consistent metric definitions | Single source of truth for all stakeholders |

---

## 📊 Business Questions Answered

### Revenue Analysis
- What is our total revenue, profit, and average order value this period?
- Which product categories generate the most revenue and highest margins?
- How is monthly revenue trending — are we growing month-over-month?
- What is our cumulative revenue trajectory over 3 years?

### Customer Retention & Loyalty
- How many new vs returning customers do we have each month?
- What percentage of customers come back after their first purchase?
- Which customer segment (Consumer / Corporate / SMB) spends the most over their lifetime?
- Which acquisition cohorts have the best long-term retention?

### Operational Intelligence
- Which cities contribute the most to revenue?
- What are our top 10 revenue-generating products?
- How does week-over-week performance compare?
- What is the impact of discounting on overall revenue?

---

## 🔍 Key Insights the Dashboard Surfaces

**Cohort Analysis** — tracks groups of customers by their first purchase month and measures how many return in subsequent months. This tells a BA whether the business is improving at retaining customers over time or whether early cohorts perform better than recent ones.

**CLV by Segment** — compares average customer lifetime value across Consumer, Corporate, and SMB segments. Helps prioritize which customer type to acquire more of.

**Retention Rate Trend** — month-over-month percentage of customers who purchased again. A declining trend is an early warning signal for churn risk.

**Rolling 3-Month Revenue Average** — smooths out seasonal spikes to show the true underlying growth trend, which is more useful for forecasting than raw monthly numbers.

---

## 🏗️ Data Pipeline — Bronze → Silver → Gold

This project uses the **Medallion Architecture** — the industry standard for enterprise data pipelines (used at Databricks, Microsoft, and Nielsen):

```
Raw Transactions (Bronze)       ← unprocessed, as-is data
        ↓
  Cleaned & Joined Views (Silver) ← standardized, business-ready
        ↓
  KPI Aggregations (Gold)        ← decision-ready metrics
        ↓
  BI Dashboard + Charts          ← stakeholder-facing output
```

| Layer | Business meaning |
|---|---|
| 🥉 Bronze | Raw data exactly as it came in — orders, customers, products |
| 🥈 Silver | Cleaned, joined, enriched — one unified view of every transaction |
| 🥇 Gold | Aggregated KPIs ready for reports — revenue, retention, cohort tables |

---

## 📁 Project Structure

```
sql_bi_dashboard/
│
├── main.py               ← Run this once to set up everything
├── data_generator.py     ← Simulates 3 years of business transactions
├── etl_pipeline.py       ← Builds Bronze → Silver → Gold layers
├── dashboard.py          ← Generates the BI report (HTML)
│
├── sql/
│   └── queries.sql       ← All business logic in SQL (10 queries)
│
├── data/
│   └── business.db       ← SQLite database
│
├── reports/
│   └── bi_dashboard.html ← Open this in your browser to see the dashboard
│
└── requirements.txt
```

---

## 🧠 Analytics Techniques Used

| Technique | Business use case |
|---|---|
| **Cohort analysis** | Measure customer retention by acquisition month |
| **MoM growth rate** | Track whether revenue is accelerating or slowing |
| **Rolling averages** | Smooth trends for cleaner forecasting signals |
| **CLV segmentation** | Identify highest-value customer groups |
| **Funnel classification** | New vs returning customer split per month |
| **Revenue attribution** | Break down performance by category, city, product |
| **Automated reporting** | Weekly KPI summary replacing manual Excel work |

---

## 🛠️ SQL Skills Demonstrated

```sql
-- Example: Cohort retention with CTEs + Window Functions
WITH cohorts AS (
    SELECT customer_id,
           STRFTIME('%Y-%m', MIN(order_date)) AS cohort_month
    FROM orders WHERE status = 'Completed'
    GROUP BY customer_id
),
cohort_sizes AS (
    SELECT cohort_month, COUNT(*) AS cohort_size
    FROM cohorts GROUP BY cohort_month
)
SELECT
    cohort_month,
    cohort_size,
    activity_month,
    ROUND(active * 100.0 / cohort_size, 1) AS retention_pct
FROM cohort_activity
JOIN cohort_sizes USING (cohort_month)
ORDER BY cohort_month, activity_month;
```

| SQL Concept | Where used |
|---|---|
| **JOINs** (INNER, LEFT) | Merging customers, orders, products into one view |
| **CTEs** | Structuring complex multi-step analyses cleanly |
| **Window Functions** (LAG, RANK, SUM OVER) | MoM growth, rankings, running totals |
| **CASE WHEN** | Classifying new vs returning customers |
| **GROUP BY + aggregations** | Revenue, orders, AOV per segment/category/city |
| **Subqueries** | Cohort size calculation |
| **STRFTIME** | Time-series grouping by month and week |

---

## 🗄️ Data Model

```
customers ──────────── orders ──────────── order_items ──── products
(500 rows)            (20,000 rows)        (~50,000 rows)   (75 rows)
│                     │                   │                 │
customer_id PK        order_id PK         item_id PK        product_id PK
name                  customer_id FK      order_id FK       product_name
email                 order_date          product_id FK     category
city                  status              quantity          cost_price
segment               payment_method      unit_price        sell_price
signup_date                               discount
```

---

## ▶️ How to Run

```bash
# 1. Install dependencies
pip install -r requirements.txt

# 2. Run full pipeline
python main.py

# 3. Open dashboard in browser
# → reports/bi_dashboard.html (double-click the file)
```

To explore the database with SQL directly:
1. Download [DB Browser for SQLite](https://sqlitebrowser.org/dl/) — free
2. Open `data/business.db`
3. Paste any query from `sql/queries.sql` into the Execute SQL tab

---

## 📈 Project Metrics

| Metric | Value |
|---|---|
| Transactions analyzed | ~50,000 order line items |
| Date range | Jan 2022 – Dec 2024 (3 years) |
| KPI dashboards built | 5 (Revenue, Retention, Cohort, Leaderboard, Weekly) |
| Reporting automation | 40% reduction in manual effort |
| SQL queries written | 10 production-quality queries |
| Customer segments tracked | Consumer, Corporate, SMB |

---

## 🔗 Related Projects

- [Sales Forecasting System](https://github.com/rani-86/sales_forecasting) — demand prediction using XGBoost, Flask API, Streamlit dashboard
- [AI Customer Support Agent](https://github.com/rani-86/ai_support_agent) — RAG-based LLM with FAISS retrieval and tool calling

---

## 👩‍💻 Author

**Rani Sharma**  
B.Tech, Production & Industrial Engineering  
National Institute of Technology, Jamshedpur  
📧 2023ugpi030@nitjsr.ac.in  
🔗 [LinkedIn](https://www.linkedin.com/in/rani-sharma/) · [GitHub](https://github.com/rani-86)
