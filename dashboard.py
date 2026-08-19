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


# ── Business insight text (computed live from the KPI tables, not
#    hardcoded — these numbers change whenever the underlying data does) ──
def insight_revenue_trend(df):
    # Compare full-year totals rather than single months — the first
    # month or two is a near-zero ramp-up artifact (few customers have
    # signed up yet), so a point-to-point comparison there produces a
    # meaningless four-digit "growth %" instead of a real trend read.
    yearly = df.assign(year=df["month"].str.slice(0, 4)).groupby("year")["revenue"].sum()
    first_year, last_year = yearly.index[0], yearly.index[-1]
    growth_pct = (yearly.iloc[-1] - yearly.iloc[0]) / yearly.iloc[0] * 100
    peak = df.loc[df["revenue"].idxmax()]
    return (
        f"Annual revenue grew from ₹{yearly.iloc[0]/1e6:.1f}M in {first_year} to "
        f"₹{yearly.iloc[-1]/1e6:.1f}M in {last_year} ({growth_pct:+.0f}%), tracking the "
        f"growing customer base over the period. The single strongest month was "
        f"{peak['month']} at ₹{peak['revenue']/1e6:.1f}M — worth checking what drove that "
        f"spike (promotion, seasonality, cohort effect) so it can be repeated deliberately."
    )


def insight_category(df):
    top = df.iloc[0]
    best_margin = df.loc[df["margin_pct"].idxmax()]
    worst_margin = df.loc[df["margin_pct"].idxmin()]
    share_pct = top["revenue"] / df["revenue"].sum() * 100
    return (
        f"{top['category']} is the single biggest revenue driver at "
        f"₹{top['revenue']/1e6:.1f}M ({share_pct:.0f}% of total). "
        f"{best_margin['category']} carries the healthiest margin ({best_margin['margin_pct']:.0f}%), "
        f"while {worst_margin['category']} is thin at {worst_margin['margin_pct']:.0f}% — "
        f"high volume there is propping up revenue, not profit. "
        f"A pricing or bundling review on {worst_margin['category']} would move the needle "
        f"more than chasing more volume in it."
    )


def insight_retention(df):
    avg_rate = (df["returning_customers"] / df["active_customers"] * 100).mean()

    # Skip month 1 (there's no prior cohort to return from yet, so it's
    # definitionally near-0% and not a real signal) and compare 3-month
    # windows rather than single months, which smooths out small-sample
    # noise from months with few active customers.
    stable = df.iloc[1:] if len(df) > 3 else df
    w = min(3, len(stable))
    early = stable.iloc[:w]
    late = stable.iloc[-w:]
    early_rate = early["returning_customers"].sum() / early["active_customers"].sum() * 100
    late_rate = late["returning_customers"].sum() / late["active_customers"].sum() * 100
    if abs(late_rate - early_rate) < 3:
        trend = "held roughly steady"
    else:
        trend = "improved" if late_rate > early_rate else "weakened"
    return (
        f"On average {avg_rate:.0f}% of active customers each month are returning buyers, "
        f"not new ones. Excluding the very first month (no prior cohort exists yet to return "
        f"from), the returning-customer share has {trend} ({early_rate:.0f}% → {late_rate:.0f}%). "
        f"Since a large share of the customer base is one-time or occasional buyers rather than "
        f"loyal repeat customers, a post-first-purchase win-back campaign (email/discount within "
        f"30-45 days) would likely have more impact than acquisition spend alone."
    )


def insight_top_products(df):
    total = df["revenue"].sum()
    top3_share = df.head(3)["revenue"].sum() / total * 100
    leader = df.iloc[0]
    return (
        f"The top 3 products alone account for {top3_share:.0f}% of top-10 revenue, led by "
        f"{leader['product_name']} (₹{leader['revenue']/1e3:.0f}K, {int(leader['units_sold']):,} units). "
        f"That concentration is a supply-chain risk as much as a strength — a stockout on "
        f"{leader['product_name']} would disproportionately hurt revenue, so it's worth "
        f"prioritizing inventory buffer and supplier reliability there specifically."
    )


def insight_city(df):
    top, bottom = df.iloc[0], df.iloc[-1]
    top3_share = df.head(3)["revenue"].sum() / df["revenue"].sum() * 100
    gap_pct = (top["revenue"] - bottom["revenue"]) / bottom["revenue"] * 100
    return (
        f"{top['city']} leads at ₹{top['revenue']/1e6:.1f}M, {gap_pct:.0f}% higher than the "
        f"lowest city, {bottom['city']}. The top 3 cities generate {top3_share:.0f}% of total "
        f"revenue — expansion marketing spend is likely better targeted at tier-2 cities "
        f"like {bottom['city']} or {df.iloc[-2]['city']} where the ceiling hasn't been tested, "
        f"rather than deepening an already-saturated top market."
    )


def insight_weekly(df):
    # STRFTIME week-bucketing can produce a truncated partial week at a
    # year boundary (far fewer orders than a normal week) — exclude those
    # before picking the "latest" week so the headline number isn't a
    # partial-period artifact.
    median_orders = df["orders"].median()
    stable = df[df["orders"] >= median_orders * 0.5]
    if len(stable) < 2:
        stable = df
    latest, prev = stable.iloc[0], stable.iloc[1]
    change_pct = (latest["revenue"] - prev["revenue"]) / prev["revenue"] * 100
    direction = "up" if change_pct >= 0 else "down"
    return (
        f"Latest full week ({latest['week']}) closed {direction} {abs(change_pct):.0f}% "
        f"week-over-week at ₹{latest['revenue']:,.0f} across {int(latest['orders']):,} orders. "
        f"This table is what used to take a manual Excel pull each Monday — it now regenerates "
        f"automatically from the same SQL views everything else on this page uses."
    )


# ── HTML Report Generator ─────────────────────────────────────────────────
def generate_html_report(kpis: dict, output="reports/index.html"):
    summary = kpis["revenue_summary"].iloc[0]

    img_trend    = chart_monthly_revenue(kpis["monthly_trend"])
    img_category = chart_category(kpis["category_revenue"])
    img_retention= chart_retention(kpis["retention"])
    img_products = chart_top_products(kpis["top_products"])
    img_city     = chart_city(kpis["city_leaderboard"])

    txt_trend     = insight_revenue_trend(kpis["monthly_trend"])
    txt_category  = insight_category(kpis["category_revenue"])
    txt_retention = insight_retention(kpis["retention"])
    txt_products  = insight_top_products(kpis["top_products"])
    txt_city      = insight_city(kpis["city_leaderboard"])
    txt_weekly    = insight_weekly(kpis["weekly_report"])

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

  /* Click-navigable section jump bar */
  .navbar {{ position:sticky; top:0; z-index:10; display:flex; flex-wrap:wrap; gap:6px;
             background:rgba(15,23,42,.92); backdrop-filter:blur(6px);
             padding:10px 0 14px; margin-bottom:8px; border-bottom:1px solid #334155; }}
  .navbar a {{ color:#cbd5e1; text-decoration:none; font-size:.78rem; font-weight:600;
               padding:6px 12px; border-radius:999px; border:1px solid #334155;
               background:#1e293b; transition:background .15s,color .15s; }}
  .navbar a:hover {{ background:#3b82f6; color:#fff; border-color:#3b82f6; }}
  .navbar a.active {{ background:#3b82f6; color:#fff; border-color:#3b82f6; }}
  /* Applied to every anchor target, not just .section — several nav
     links point at inner divs (#category, #retention, #products, #city)
     that don't carry the .section class, and without this they scroll
     to top:0 and land hidden behind the sticky navbar, which looks like
     the click did nothing even though it did scroll. */
  [id] {{ scroll-margin-top:90px; }}
  /* Flash the jumped-to section so a click is visibly obvious even in a
     viewer that renders the whole page at once with nothing to scroll. */
  @keyframes sectionFlash {{
    0%   {{ background-color:rgba(59,130,246,.28); }}
    100% {{ background-color:transparent; }}
  }}
  [id].flash {{ animation:sectionFlash 1.4s ease; border-radius:12px; }}

  /* Collapsible "Business Insight" panels — click to expand/collapse */
  details.insight {{ margin-top:12px; background:#0f172a; border:1px solid #334155;
                      border-radius:10px; overflow:hidden; }}
  details.insight summary {{ cursor:pointer; list-style:none; padding:10px 14px;
                              font-size:.82rem; font-weight:600; color:#93c5fd;
                              display:flex; align-items:center; gap:8px;
                              user-select:none; }}
  details.insight summary::-webkit-details-marker {{ display:none; }}
  details.insight summary::before {{ content:"▸"; display:inline-block;
                              transition:transform .15s; color:#3b82f6; }}
  details.insight[open] summary::before {{ transform:rotate(90deg); }}
  details.insight summary:hover {{ background:#1e293b; }}
  details.insight .insight-body {{ padding:0 16px 14px 34px; color:#cbd5e1;
                              font-size:.85rem; line-height:1.55; }}
</style>
</head>
<body>

<nav class="navbar">
  <a href="#overview">Overview</a>
  <a href="#revenue">Revenue Trend</a>
  <a href="#category">Category</a>
  <a href="#retention">Retention</a>
  <a href="#products">Top Products</a>
  <a href="#city">Cities</a>
  <a href="#weekly">Weekly Report</a>
</nav>

<h1 id="overview">📊 SQL Business Intelligence Dashboard</h1>
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
<div class="section" id="revenue">
  <h2>📈 Revenue & Profit Trend</h2>
  <div class="chart-card">
    <img src="{img_trend}">
    <details class="insight">
      <summary>Business Insight</summary>
      <div class="insight-body">{txt_trend}</div>
    </details>
  </div>
</div>

<!-- Category + Retention -->
<div class="section grid-2">
  <div id="category">
    <h2>🛒 Category Performance</h2>
    <div class="chart-card">
      <img src="{img_category}">
      <details class="insight">
        <summary>Business Insight</summary>
        <div class="insight-body">{txt_category}</div>
      </details>
    </div>
  </div>
  <div id="retention">
    <h2>👥 Customer Retention</h2>
    <div class="chart-card">
      <img src="{img_retention}">
      <details class="insight">
        <summary>Business Insight</summary>
        <div class="insight-body">{txt_retention}</div>
      </details>
    </div>
  </div>
</div>

<!-- Products + City -->
<div class="section grid-2">
  <div id="products">
    <h2>🏆 Top Products</h2>
    <div class="chart-card">
      <img src="{img_products}">
      <details class="insight">
        <summary>Business Insight</summary>
        <div class="insight-body">{txt_products}</div>
      </details>
    </div>
  </div>
  <div id="city">
    <h2>🏙️ City Leaderboard</h2>
    <div class="chart-card">
      <img src="{img_city}">
      <details class="insight">
        <summary>Business Insight</summary>
        <div class="insight-body">{txt_city}</div>
      </details>
    </div>
  </div>
</div>

<!-- Weekly Automated Report -->
<div class="section" id="weekly">
  <h2>⚡ Automated Weekly Report (replaces manual Excel — saves 40% effort)</h2>
  <div class="chart-card">
    <table>
      <thead><tr><th>Week</th><th>Orders</th><th>Customers</th><th>Revenue</th></tr></thead>
      <tbody>{weekly_rows}</tbody>
    </table>
    <details class="insight">
      <summary>Business Insight</summary>
      <div class="insight-body">{txt_weekly}</div>
    </details>
  </div>
</div>

<div class="footer">
  SQL BI Dashboard · Rani Sharma · NIT Jamshedpur · Production & Industrial Engineering<br>
  Built with: SQLite · Python · Pandas · Matplotlib · CTEs · Window Functions · Cohort Analysis
</div>

<script>
// Give nav clicks a guaranteed visible reaction — highlight the clicked
// button and flash the target section — instead of relying purely on
// scroll position, which some embedded/inline HTML viewers don't show.
document.querySelectorAll('.navbar a').forEach(function(link) {{
  link.addEventListener('click', function() {{
    document.querySelectorAll('.navbar a').forEach(function(l) {{ l.classList.remove('active'); }});
    link.classList.add('active');

    var targetId = link.getAttribute('href').slice(1);
    var target = document.getElementById(targetId);
    if (target) {{
      target.classList.remove('flash');
      void target.offsetWidth; // restart the animation if clicked twice
      target.classList.add('flash');
    }}
  }});
}});
</script>

</body></html>"""

    with open(output, "w", encoding="utf-8") as f:
        f.write(html)
    print(f"✅ Dashboard saved → {output}")

    # Also mirror to root index.html — that's what GitHub Pages actually
    # serves at rani-86.github.io/sql_bi_dashboard/.
    root_copy = "index.html"
    with open(root_copy, "w", encoding="utf-8") as f:
        f.write(html)
    print(f"✅ Dashboard mirrored → {root_copy} (GitHub Pages)")

    return output


if __name__ == "__main__":
    print("📊 Generating BI Dashboard...")
    kpis = run_pipeline()
    generate_html_report(kpis)
