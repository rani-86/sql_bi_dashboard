"""
dashboard.py
Generates a full HTML Business Intelligence report with all KPI charts.
Run: python dashboard.py
Output: reports/bi_dashboard.html
"""

import sqlite3
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.ticker as mticker
import base64, io, os
from etl_pipeline import run_pipeline

os.makedirs("reports", exist_ok=True)

# ── Chart helpers ─────────────────────────────────────────────────────────
DARK  = "#0f172a"
CARD  = "#1e293b"
BLUE  = "#3b82f6"
GREEN = "#10b981"
PURP  = "#8b5cf6"
ORG   = "#f59e0b"
RED   = "#ef4444"
TEXT  = "#f1f5f9"
MUTED = "#94a3b8"

def fig_to_b64(fig):
    buf = io.BytesIO()
    fig.savefig(buf, format="png", bbox_inches="tight",
                facecolor=DARK, dpi=120)
    buf.seek(0)
    b64 = base64.b64encode(buf.read()).decode()
    plt.close(fig)
    return f"data:image/png;base64,{b64}"


def chart_monthly_revenue(df):
    fig, ax = plt.subplots(figsize=(10, 4), facecolor=DARK)
    ax.set_facecolor(DARK)
    ax.plot(df["month"], df["revenue"], color=BLUE,  lw=2, label="Revenue")
    ax.plot(df["month"], df["profit"],  color=GREEN, lw=2, label="Profit", linestyle="--")
    ax.fill_between(df["month"], df["revenue"], alpha=0.12, color=BLUE)
    ax.set_title("Monthly Revenue & Profit Trend", color=TEXT, fontsize=13, pad=12)
    ax.tick_params(colors=MUTED, labelsize=8)
    ax.xaxis.set_major_locator(mticker.MultipleLocator(6))
    plt.xticks(rotation=45)
    ax.spines[["top","right","left","bottom"]].set_color("#334155")
    ax.yaxis.set_major_formatter(mticker.FuncFormatter(lambda x,_: f"₹{x/1e6:.1f}M"))
    ax.legend(facecolor=CARD, labelcolor=TEXT, fontsize=9)
    fig.tight_layout()
    return fig_to_b64(fig)


def chart_category(df):
    fig, axes = plt.subplots(1, 2, figsize=(10, 4), facecolor=DARK)
    colors = [BLUE, GREEN, PURP, ORG, RED]

    ax1 = axes[0]; ax1.set_facecolor(DARK)
    bars = ax1.barh(df["category"], df["revenue"], color=colors[:len(df)])
    ax1.set_title("Revenue by Category", color=TEXT, fontsize=11, pad=8)
    ax1.tick_params(colors=MUTED, labelsize=9)
    ax1.spines[["top","right","left","bottom"]].set_color("#334155")
    ax1.xaxis.set_major_formatter(mticker.FuncFormatter(lambda x,_: f"₹{x/1e6:.1f}M"))
    for bar, val in zip(bars, df["revenue"]):
        ax1.text(bar.get_width()*0.98, bar.get_y()+bar.get_height()/2,
                 f"₹{val/1e6:.1f}M", va="center", ha="right", color=DARK, fontsize=8, fontweight="bold")

    ax2 = axes[1]; ax2.set_facecolor(DARK)
    ax2.bar(df["category"], df["margin_pct"], color=GREEN, alpha=0.8)
    ax2.set_title("Profit Margin % by Category", color=TEXT, fontsize=11, pad=8)
    ax2.tick_params(colors=MUTED, labelsize=9)
    ax2.spines[["top","right","left","bottom"]].set_color("#334155")
    ax2.set_ylabel("%", color=MUTED)
    plt.xticks(rotation=20)

    fig.tight_layout()
    return fig_to_b64(fig)


def chart_retention(df):
    fig, axes = plt.subplots(1, 2, figsize=(10, 4), facecolor=DARK)

    ax1 = axes[0]; ax1.set_facecolor(DARK)
    ax1.bar(df["month"], df["new_customers"],       color=GREEN, label="New",       alpha=0.9)
    ax1.bar(df["month"], df["returning_customers"], color=BLUE,  label="Returning", alpha=0.9,
            bottom=df["new_customers"])
    ax1.set_title("New vs Returning Customers", color=TEXT, fontsize=11, pad=8)
    ax1.tick_params(colors=MUTED, labelsize=7)
    ax1.xaxis.set_major_locator(mticker.MultipleLocator(4))
    plt.setp(ax1.xaxis.get_majorticklabels(), rotation=45)
    ax1.spines[["top","right","left","bottom"]].set_color("#334155")
    ax1.legend(facecolor=CARD, labelcolor=TEXT, fontsize=9)

    ax2 = axes[1]; ax2.set_facecolor(DARK)
    ret_rate = df["returning_customers"] / df["active_customers"] * 100
    ax2.plot(df["month"], ret_rate, color=PURP, lw=2, marker="o", markersize=3)
    ax2.fill_between(df["month"], ret_rate, alpha=0.15, color=PURP)
    ax2.set_title("Retention Rate %", color=TEXT, fontsize=11, pad=8)
    ax2.tick_params(colors=MUTED, labelsize=7)
    ax2.xaxis.set_major_locator(mticker.MultipleLocator(4))
    plt.setp(ax2.xaxis.get_majorticklabels(), rotation=45)
    ax2.spines[["top","right","left","bottom"]].set_color("#334155")
    ax2.set_ylabel("%", color=MUTED)

    fig.tight_layout()
    return fig_to_b64(fig)


def chart_top_products(df):
    fig, ax = plt.subplots(figsize=(10, 4), facecolor=DARK)
    ax.set_facecolor(DARK)
    colors = [BLUE if i < 3 else MUTED for i in range(len(df))]
    bars = ax.barh(df["product_name"][::-1], df["revenue"][::-1], color=colors[::-1])
    ax.set_title("Top 10 Products by Revenue", color=TEXT, fontsize=11, pad=8)
    ax.tick_params(colors=MUTED, labelsize=8)
    ax.spines[["top","right","left","bottom"]].set_color("#334155")
    ax.xaxis.set_major_formatter(mticker.FuncFormatter(lambda x,_: f"₹{x/1e3:.0f}K"))
    fig.tight_layout()
    return fig_to_b64(fig)


def chart_city(df):
    fig, ax = plt.subplots(figsize=(10, 4), facecolor=DARK)
    ax.set_facecolor(DARK)
    ax.bar(df["city"], df["revenue"], color=ORG, alpha=0.85)
    ax.set_title("Revenue by City", color=TEXT, fontsize=11, pad=8)
    ax.tick_params(colors=MUTED, labelsize=9)
    ax.spines[["top","right","left","bottom"]].set_color("#334155")
    ax.yaxis.set_major_formatter(mticker.FuncFormatter(lambda x,_: f"₹{x/1e6:.1f}M"))
    plt.xticks(rotation=20)
    fig.tight_layout()
    return fig_to_b64(fig)


# ── HTML Report Generator ─────────────────────────────────────────────────
def generate_html_report(kpis: dict, output="reports/bi_dashboard.html"):
    summary = kpis["revenue_summary"].iloc[0]

    img_trend    = chart_monthly_revenue(kpis["monthly_trend"])
    img_category = chart_category(kpis["category_revenue"])
    img_retention= chart_retention(kpis["retention"])
    img_products = chart_top_products(kpis["top_products"])
    img_city     = chart_city(kpis["city_leaderboard"])

    weekly_rows = ""
    for _, r in kpis["weekly_report"].iterrows():
        weekly_rows += f"""
        <tr>
          <td>{r['week']}</td>
          <td>{int(r['orders']):,}</td>
          <td>{int(r['customers']):,}</td>
          <td>₹{r['revenue']:,.0f}</td>
        </tr>"""

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>SQL BI Dashboard — Rani Sharma</title>
<style>
  * {{ box-sizing:border-box; margin:0; padding:0; }}
  body {{ background:#0f172a; color:#f1f5f9; font-family:'Segoe UI',sans-serif; padding:24px; }}
  h1 {{ font-size:1.6rem; color:#f1f5f9; margin-bottom:4px; }}
  .subtitle {{ color:#94a3b8; font-size:.9rem; margin-bottom:24px; }}
  .badge {{ background:#1d4ed8; color:#bfdbfe; font-size:.75rem;
            padding:2px 10px; border-radius:999px; margin-right:6px; }}
  .kpi-row {{ display:grid; grid-template-columns:repeat(4,1fr); gap:16px; margin-bottom:24px; }}
  .kpi {{ background:#1e293b; border-radius:12px; padding:18px; border:1px solid #334155; }}
  .kpi .label {{ color:#94a3b8; font-size:.8rem; margin-bottom:4px; }}
  .kpi .value {{ font-size:1.5rem; font-weight:700; color:#f1f5f9; }}
  .kpi .sub   {{ font-size:.75rem; color:#10b981; margin-top:2px; }}
  .section {{ margin-bottom:28px; }}
  .section h2 {{ font-size:1rem; color:#94a3b8; text-transform:uppercase;
                 letter-spacing:.08em; margin-bottom:12px; }}
  .chart-card {{ background:#1e293b; border-radius:12px; padding:16px;
                  border:1px solid #334155; }}
  .chart-card img {{ width:100%; border-radius:8px; }}
  .grid-2 {{ display:grid; grid-template-columns:1fr 1fr; gap:16px; }}
  table {{ width:100%; border-collapse:collapse; }}
  th,td {{ padding:10px 14px; text-align:left; border-bottom:1px solid #334155;
            font-size:.85rem; }}
  th {{ color:#94a3b8; font-weight:600; background:#0f172a; }}
  tr:hover td {{ background:#1e293b; }}
  .footer {{ text-align:center; color:#475569; font-size:.8rem; margin-top:32px; }}
  .arch-badge {{ display:inline-block; padding:3px 12px; border-radius:6px;
                  font-size:.78rem; font-weight:600; margin:2px; }}
  .bronze {{ background:#92400e; color:#fde68a; }}
  .silver {{ background:#334155; color:#e2e8f0; }}
  .gold   {{ background:#78350f; color:#fef3c7; }}
</style>
</head>
<body>

<h1>📊 SQL Business Intelligence Dashboard</h1>
<p class="subtitle">
  <span class="badge">SQL</span>
  <span class="badge">CTEs</span>
  <span class="badge">Window Functions</span>
  <span class="badge">Cohort Analysis</span>
  <span class="badge">ETL Automation</span>
  &nbsp;|&nbsp; Rani Sharma · NIT Jamshedpur
</p>

<div style="margin-bottom:16px;">
  <span class="arch-badge bronze">🥉 Bronze: Raw Tables</span>
  <span style="color:#475569">→</span>
  <span class="arch-badge silver">🥈 Silver: Enriched Views</span>
  <span style="color:#475569">→</span>
  <span class="arch-badge gold">🥇 Gold: KPI Tables</span>
</div>

<!-- KPI Cards -->
<div class="kpi-row">
  <div class="kpi">
    <div class="label">Total Revenue</div>
    <div class="value">₹{summary['total_revenue']/1e6:.1f}M</div>
    <div class="sub">Completed orders only</div>
  </div>
  <div class="kpi">
    <div class="label">Total Profit</div>
    <div class="value">₹{summary['total_profit']/1e6:.1f}M</div>
    <div class="sub">Margin: {summary['profit_margin_pct']}%</div>
  </div>
  <div class="kpi">
    <div class="label">Total Orders</div>
    <div class="value">{int(summary['total_orders']):,}</div>
    <div class="sub">Completed transactions</div>
  </div>
  <div class="kpi">
    <div class="label">Avg Order Value</div>
    <div class="value">₹{summary['avg_order_value']:,.0f}</div>
    <div class="sub">Per completed order</div>
  </div>
</div>

<!-- Revenue Trend -->
<div class="section">
  <h2>📈 Revenue & Profit Trend</h2>
  <div class="chart-card"><img src="{img_trend}"></div>
</div>

<!-- Category + Retention -->
<div class="section grid-2">
  <div>
    <h2>🛒 Category Performance</h2>
    <div class="chart-card"><img src="{img_category}"></div>
  </div>
  <div>
    <h2>👥 Customer Retention</h2>
    <div class="chart-card"><img src="{img_retention}"></div>
  </div>
</div>

<!-- Products + City -->
<div class="section grid-2">
  <div>
    <h2>🏆 Top Products</h2>
    <div class="chart-card"><img src="{img_products}"></div>
  </div>
  <div>
    <h2>🏙️ City Leaderboard</h2>
    <div class="chart-card"><img src="{img_city}"></div>
  </div>
</div>

<!-- Weekly Automated Report -->
<div class="section">
  <h2>⚡ Automated Weekly Report (replaces manual Excel — saves 40% effort)</h2>
  <div class="chart-card">
    <table>
      <thead><tr><th>Week</th><th>Orders</th><th>Customers</th><th>Revenue</th></tr></thead>
      <tbody>{weekly_rows}</tbody>
    </table>
  </div>
</div>

<div class="footer">
  SQL BI Dashboard · Rani Sharma · NIT Jamshedpur · Production & Industrial Engineering<br>
  Built with: SQLite · Python · Pandas · Matplotlib · CTEs · Window Functions · Cohort Analysis
</div>

</body></html>"""

    with open(output, "w") as f:
        f.write(html)
    print(f"✅ Dashboard saved → {output}")
    return output


if __name__ == "__main__":
    print("📊 Generating BI Dashboard...")
    kpis = run_pipeline()
    generate_html_report(kpis)
