"""
main.py
Master runner — runs full pipeline in sequence.
Run this first!
"""

from data_generator import setup_database
from etl_pipeline import run_pipeline
from dashboard import generate_html_report

if __name__ == "__main__":
    print("=" * 60)
    print("  SQL BUSINESS INTELLIGENCE DASHBOARD")
    print("  Rani Sharma | NIT Jamshedpur")
    print("  Bronze → Silver → Gold Architecture")
    print("=" * 60)

    print("\n[1/3] Setting up SQLite database...")
    setup_database()

    print("\n[2/3] Running ETL pipeline (Bronze → Silver → Gold)...")
    kpis = run_pipeline()

    print("[3/3] Generating HTML dashboard...")
    output = generate_html_report(kpis)

    print("\n" + "=" * 60)
    print("✅ PROJECT COMPLETE!")
    print("=" * 60)
    print(f"""
📊 Open your dashboard:
   → reports/bi_dashboard.html  (open in any browser)

🗄️  Explore the database:
   → data/business.db  (open with DB Browser for SQLite)

📝 View all SQL queries:
   → sql/queries.sql

▶️  Re-run anytime:
   python main.py
""")
    print("=" * 60)
