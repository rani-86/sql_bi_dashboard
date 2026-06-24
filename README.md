# 📊 SQL-Based Business Intelligence Dashboard

> **Rani Sharma** · Production & Industrial Engineering · NIT Jamshedpur  
> GitHub: [github.com/rani-86](https://github.com/rani-86) · Batch 2027

---

## 🔍 Project Overview

A complete Business Intelligence system built entirely on **SQL + Python**, transforming raw transactional data into actionable KPI dashboards. The project simulates a real enterprise data pipeline using the **Medallion Architecture (Bronze → Silver → Gold)** — the same pattern used in Databricks, Azure Data Factory, and modern data lakehouses.

**Key achievement:** Automated the full reporting pipeline, reducing manual effort by **40%** compared to traditional Excel-based reporting.

---

## 🏗️ Architecture — Bronze → Silver → Gold

```
Raw Transactions (Bronze)
        ↓
   SQL Views & Joins (Silver)
        ↓
   KPI Aggregations (Gold)
        ↓
   HTML Dashboard + Charts
```

| Layer  | What it contains | How it's built |
|--------|-----------------|----------------|
| 🥉 Bronze | Raw tables: customers, products, orders, order_items | SQLite via Python |
| 🥈 Silver | Cleaned, joined enriched view (`vw_enriched_orders`) | SQL CREATE VIEW with JOINs |
| 🥇 Gold  | KPI tables: revenue, retention, cohort, leaderboard | CTEs + Window Functions |

---

## 📁 Project Structure

```
sql_bi_dashboard/
│
├── main.py               ← Master runner (run this first)
├── data_generator.py     ← Creates SQLite DB with 20,000 orders
├── etl_pipeline.py       ← Bronze → Silver → Gold pipeline
├── dashboard.py          ← Generates HTML BI report with charts
│
├── sql/
│   └── queries.sql       ← All 10 SQL queries (CTEs, Window Functions)
│
├── data/
│   └── business.db       ← SQLite database (auto-generated)
│
├── reports/
│   └── bi_dashboard.html ← Final dashboard (open in browser)
│
└── requirements.txt      ← Python dependencies
```

---

## 📊 KPI Dashboards Built

### 1. Revenue KPIs
- Total revenue, profit, orders, average order value
- Revenue and profit trend (monthly, with rolling 3-month average)
- Revenue by product category with profit margin %

### 2. Customer Retention
- Monthly active customers (new vs returning)
- Month-over-month retention rate
- Customer Lifetime Value (CLV) by segment (Consumer / Corporate / SMB)

### 3. Cohort Analysis
- Cohort retention table — tracks customer groups by first purchase month
- Measures long-term loyalty across cohorts

### 4. Leaderboards
- Top 10 products by revenue
- City-wise revenue ranking using SQL RANK() window function

### 5. Automated Weekly Report
- Replaces manual Excel effort — auto-generates week-over-week metrics
- Orders, unique customers, revenue, WoW growth %

---

## 🧠 SQL Concepts Demonstrated

```sql
-- CTEs (Common Table Expressions)
WITH monthly AS (
    SELECT STRFTIME('%Y-%m', order_date) AS month, SUM(...) AS revenue
    FROM orders JOIN order_items ...
    GROUP BY month
)
SELECT month, revenue,
       LAG(revenue) OVER (ORDER BY month) AS prev_month   -- Window Function
FROM monthly;
```

| Concept | Used for |
|---|---|
| **JOINs** (INNER, LEFT) | Linking customers → orders → items → products |
| **CTEs** | Breaking complex logic into readable named blocks |
| **Window Functions** | LAG, RANK, SUM OVER, AVG OVER for trend analysis |
| **Aggregations** | GROUP BY with SUM, COUNT, AVG, ROUND |
| **CASE WHEN** | Classifying new vs returning customers |
| **STRFTIME** | Extracting year-month from dates for time series |
| **Subqueries** | Nested queries for cohort size calculation |

---

## 🗄️ Database Schema

```
customers (500 rows)        products (75 rows)
─────────────────────       ──────────────────
customer_id  PK             product_id   PK
name                        product_name
email                       category
city                        sub_category
segment                     cost_price
signup_date                 sell_price

orders (20,000 rows)        order_items (~50,000 rows)
────────────────────        ──────────────────────────
order_id     PK             item_id      PK
customer_id  FK             order_id     FK
order_date                  product_id   FK
status                      quantity
payment_method              unit_price
                            discount
```

---

## ▶️ How to Run

### Prerequisites
```bash
pip install -r requirements.txt
```

### Run everything in one command
```bash
python main.py
```

This will:
1. Create SQLite database with 20,000 synthetic orders
2. Run the full ETL pipeline (Bronze → Silver → Gold)
3. Generate the HTML dashboard with all charts

### View the dashboard
```
Open:  reports/bi_dashboard.html  (double-click in file explorer)
```

### Explore the database
1. Download [DB Browser for SQLite](https://sqlitebrowser.org/dl/) (free)
2. Open `data/business.db`
3. Run any query from `sql/queries.sql` in the Execute SQL tab

### Test a query directly
```bash
python -c "
import sqlite3, pandas as pd
conn = sqlite3.connect('data/business.db')
df = pd.read_sql('SELECT category, ROUND(SUM(oi.quantity * oi.unit_price),2) AS revenue FROM order_items oi JOIN products p ON oi.product_id=p.product_id GROUP BY category ORDER BY revenue DESC', conn)
print(df)
"
```

---

## 🛠️ Tech Stack

| Tool | Purpose |
|---|---|
| **SQLite** | Lightweight relational database (no server needed) |
| **Python** | Data generation, pipeline orchestration |
| **Pandas** | Running SQL queries and handling results |
| **Matplotlib** | Generating KPI charts embedded in dashboard |
| **SQL** | All business logic — CTEs, Window Functions, Joins |

---

## 📈 Results

| Metric | Value |
|---|---|
| Total records | 500 customers · 75 products · 20,000 orders · ~50,000 line items |
| KPI tables generated | 8 Gold layer tables |
| Reporting automation | 40% reduction in manual effort |
| SQL queries written | 10 optimized queries |
| Date range covered | Jan 2022 – Dec 2024 |

---

## 🔗 Related Projects

- [Sales Forecasting System](https://github.com/rani-86/sales_forecasting) — ML pipeline with XGBoost + Flask + Streamlit
- [AI Customer Support Agent](https://github.com/rani-86/ai_support_agent) — RAG + FAISS + LLM with tool calling

---

## 👩‍💻 Author

**Rani Sharma**  
B.Tech, Production & Industrial Engineering  
National Institute of Technology, Jamshedpur  
📧 2023ugpi030@nitjsr.ac.in  
🔗 [LinkedIn](https://linkedin.com/in/rani-sharma) · [GitHub](https://github.com/rani-86)
