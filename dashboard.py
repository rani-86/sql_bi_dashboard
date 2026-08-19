"""
dashboard.py
Generates a full HTML Business Intelligence report with interactive charts
(Chart.js — hover tooltips, click-to-toggle series in the legend) instead
of static images, plus auto-computed business insight panels.
Run: python dashboard.py
Output: reports/index.html (mirrored to root index.html for GitHub Pages)
"""

import json
import os
from etl_pipeline import run_pipeline

os.makedirs("reports", exist_ok=True)

# ── Palette (shared between CSS and Chart.js configs) ─────────────────────
DARK  = "#0f172a"
CARD  = "#1e293b"
BLUE  = "#3b82f6"
GREEN = "#10b981"
PURP  = "#8b5cf6"
ORG   = "#f59e0b"
RED   = "#ef4444"
TEXT  = "#f1f5f9"
MUTED = "#94a3b8"
GRID  = "#1e293b"


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


def insight_top_customers(df):
    leader = df.iloc[0]
    top10_total = df["lifetime_revenue"].sum()
    corporate_count = (df["segment"] == "Corporate").sum()
    return (
        f"{leader['customer_name']} is the highest-LTV customer at "
        f"₹{leader['lifetime_revenue']:,.0f} across {int(leader['total_orders'])} orders. "
        f"{corporate_count} of the top 10 are Corporate-segment accounts — "
        f"if that segment is over-represented here relative to its share of the "
        f"total customer base, it's a signal to prioritize account management "
        f"for Corporate customers specifically rather than treating all segments "
        f"the same in retention efforts."
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


# ── Chart.js data + config builder ─────────────────────────────────────────
# All charts are real Chart.js instances (not static images): hovering
# shows a tooltip with the exact figure, and clicking a legend entry
# toggles that series on/off — genuine interactivity, not just navigation.
def build_chart_script(kpis):
    trend = kpis["monthly_trend"]
    category = kpis["category_revenue"]
    retention = kpis["retention"]
    products = kpis["top_products"]
    city = kpis["city_leaderboard"]

    ret_rate = (retention["returning_customers"] / retention["active_customers"] * 100).round(1)

    data = {
        "trendLabels": list(trend["month"]),
        "trendRevenue": [round(float(v), 2) for v in trend["revenue"]],
        "trendProfit": [round(float(v), 2) for v in trend["profit"]],

        "catLabels": list(category["category"]),
        "catRevenue": [round(float(v), 2) for v in category["revenue"]],
        "catMargin": [round(float(v), 2) for v in category["margin_pct"]],

        "retMonths": list(retention["month"]),
        "retNew": [int(v) for v in retention["new_customers"]],
        "retReturning": [int(v) for v in retention["returning_customers"]],
        "retRate": [round(float(v), 1) for v in ret_rate],

        # Charted bottom-to-top (largest at top) — matching the original
        # horizontal-bar layout.
        "prodLabels": list(products["product_name"])[::-1],
        "prodRevenue": [round(float(v), 2) for v in products["revenue"]][::-1],

        "cityLabels": list(city["city"]),
        "cityRevenue": [round(float(v), 2) for v in city["revenue"]],
    }
    d = json.dumps(data)

    return f"""
const D = {d};
const TEXT_COLOR = "{TEXT}";
const MUTED_COLOR = "{MUTED}";
const GRID_COLOR = "{GRID}";

Chart.defaults.color = MUTED_COLOR;
Chart.defaults.font.family = "'Segoe UI', sans-serif";

function fmtM(v) {{ return "₹" + (v / 1e6).toFixed(1) + "M"; }}
function fmtK(v) {{ return "₹" + (v / 1e3).toFixed(0) + "K"; }}

new Chart(document.getElementById("chartTrend"), {{
  type: "line",
  data: {{
    labels: D.trendLabels,
    datasets: [
      {{ label: "Revenue", data: D.trendRevenue, borderColor: "{BLUE}",
         backgroundColor: "rgba(59,130,246,.15)", fill: true, tension: .3, pointRadius: 0 }},
      {{ label: "Profit", data: D.trendProfit, borderColor: "{GREEN}",
         borderDash: [6, 4], fill: false, tension: .3, pointRadius: 0 }}
    ]
  }},
  options: {{
    responsive: true,
    interaction: {{ mode: "index", intersect: false }},
    plugins: {{
      legend: {{ labels: {{ color: TEXT_COLOR }} }},
      tooltip: {{ callbacks: {{ label: ctx => ctx.dataset.label + ": " + fmtM(ctx.parsed.y) }} }}
    }},
    scales: {{
      x: {{ ticks: {{ maxTicksLimit: 12 }}, grid: {{ color: GRID_COLOR }} }},
      y: {{ ticks: {{ callback: fmtM }}, grid: {{ color: GRID_COLOR }} }}
    }}
  }}
}});

new Chart(document.getElementById("chartCategoryRevenue"), {{
  type: "bar",
  data: {{
    labels: D.catLabels,
    datasets: [{{ label: "Revenue", data: D.catRevenue,
      backgroundColor: ["{BLUE}", "{GREEN}", "{PURP}", "{ORG}", "{RED}"] }}]
  }},
  options: {{
    indexAxis: "y", responsive: true,
    plugins: {{ legend: {{ display: false }},
      tooltip: {{ callbacks: {{ label: ctx => fmtM(ctx.parsed.x) }} }} }},
    scales: {{
      x: {{ ticks: {{ callback: fmtM }}, grid: {{ color: GRID_COLOR }} }},
      y: {{ grid: {{ display: false }} }}
    }}
  }}
}});

new Chart(document.getElementById("chartCategoryMargin"), {{
  type: "bar",
  data: {{
    labels: D.catLabels,
    datasets: [{{ label: "Margin %", data: D.catMargin, backgroundColor: "{GREEN}" }}]
  }},
  options: {{
    responsive: true,
    plugins: {{ legend: {{ display: false }},
      tooltip: {{ callbacks: {{ label: ctx => ctx.parsed.y + "%" }} }} }},
    scales: {{
      x: {{ grid: {{ display: false }} }},
      y: {{ ticks: {{ callback: v => v + "%" }}, grid: {{ color: GRID_COLOR }} }}
    }}
  }}
}});

new Chart(document.getElementById("chartRetentionSplit"), {{
  type: "bar",
  data: {{
    labels: D.retMonths,
    datasets: [
      {{ label: "New", data: D.retNew, backgroundColor: "{GREEN}", stack: "s" }},
      {{ label: "Returning", data: D.retReturning, backgroundColor: "{BLUE}", stack: "s" }}
    ]
  }},
  options: {{
    responsive: true,
    plugins: {{ legend: {{ labels: {{ color: TEXT_COLOR }} }} }},
    scales: {{
      x: {{ stacked: true, ticks: {{ maxTicksLimit: 10 }} }},
      y: {{ stacked: true, grid: {{ color: GRID_COLOR }} }}
    }}
  }}
}});

new Chart(document.getElementById("chartRetentionRate"), {{
  type: "line",
  data: {{
    labels: D.retMonths,
    datasets: [{{ label: "Retention Rate %", data: D.retRate, borderColor: "{PURP}",
      backgroundColor: "rgba(139,92,246,.15)", fill: true, tension: .3, pointRadius: 0 }}]
  }},
  options: {{
    responsive: true,
    plugins: {{ legend: {{ display: false }},
      tooltip: {{ callbacks: {{ label: ctx => ctx.parsed.y + "%" }} }} }},
    scales: {{
      x: {{ ticks: {{ maxTicksLimit: 10 }} }},
      y: {{ ticks: {{ callback: v => v + "%" }}, grid: {{ color: GRID_COLOR }} }}
    }}
  }}
}});

new Chart(document.getElementById("chartProducts"), {{
  type: "bar",
  data: {{
    labels: D.prodLabels,
    datasets: [{{ label: "Revenue", data: D.prodRevenue,
      backgroundColor: D.prodLabels.map((_, i) => i >= D.prodLabels.length - 3 ? "{BLUE}" : "{MUTED}") }}]
  }},
  options: {{
    indexAxis: "y", responsive: true,
    plugins: {{ legend: {{ display: false }},
      tooltip: {{ callbacks: {{ label: ctx => fmtK(ctx.parsed.x) }} }} }},
    scales: {{
      x: {{ ticks: {{ callback: fmtK }}, grid: {{ color: GRID_COLOR }} }},
      y: {{ grid: {{ display: false }} }}
    }}
  }}
}});

new Chart(document.getElementById("chartCity"), {{
  type: "bar",
  data: {{
    labels: D.cityLabels,
    datasets: [{{ label: "Revenue", data: D.cityRevenue, backgroundColor: "{ORG}" }}]
  }},
  options: {{
    responsive: true,
    plugins: {{ legend: {{ display: false }},
      tooltip: {{ callbacks: {{ label: ctx => fmtM(ctx.parsed.y) }} }} }},
    scales: {{
      x: {{ grid: {{ display: false }} }},
      y: {{ ticks: {{ callback: fmtM }}, grid: {{ color: GRID_COLOR }} }}
    }}
  }}
}});
"""


# ── HTML Report Generator ─────────────────────────────────────────────────
def generate_html_report(kpis: dict, output="reports/index.html"):
    summary = kpis["revenue_summary"].iloc[0]

    txt_trend     = insight_revenue_trend(kpis["monthly_trend"])
    txt_category  = insight_category(kpis["category_revenue"])
    txt_retention = insight_retention(kpis["retention"])
    txt_products  = insight_top_products(kpis["top_products"])
    txt_city      = insight_city(kpis["city_leaderboard"])
    txt_customers = insight_top_customers(kpis["top_customers"])
    txt_weekly    = insight_weekly(kpis["weekly_report"])

    chart_script = build_chart_script(kpis)

    weekly_rows = ""
    for _, r in kpis["weekly_report"].iterrows():
        weekly_rows += f"""
        <tr>
          <td>{r['week']}</td>
          <td>{int(r['orders']):,}</td>
          <td>{int(r['customers']):,}</td>
          <td>₹{r['revenue']:,.0f}</td>
        </tr>"""

    customer_rows = ""
    for _, r in kpis["top_customers"].iterrows():
        customer_rows += f"""
        <tr>
          <td>#{int(r['ltv_rank'])}</td>
          <td>{r['customer_name']}</td>
          <td>{r['segment']}</td>
          <td>{r['city']}</td>
          <td>{int(r['total_orders'])}</td>
          <td>₹{r['lifetime_revenue']:,.0f}</td>
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
  .chart-card canvas {{ max-height:320px; }}
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
  <a href="#customers">Top Customers</a>
  <a href="#weekly">Weekly Report</a>
</nav>

<h1 id="overview">📊 SQL Business Intelligence Dashboard</h1>
<p class="subtitle">
  <span class="badge">SQL</span>
  <span class="badge">CTEs</span>
  <span class="badge">Window Functions</span>
  <span class="badge">Triggers</span>
  <span class="badge">Cohort Analysis</span>
  <span class="badge">Interactive Charts</span>
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
    <canvas id="chartTrend" height="90"></canvas>
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
      <canvas id="chartCategoryRevenue" height="150"></canvas>
      <canvas id="chartCategoryMargin" height="120" style="margin-top:12px;"></canvas>
      <details class="insight">
        <summary>Business Insight</summary>
        <div class="insight-body">{txt_category}</div>
      </details>
    </div>
  </div>
  <div id="retention">
    <h2>👥 Customer Retention</h2>
    <div class="chart-card">
      <canvas id="chartRetentionSplit" height="150"></canvas>
      <canvas id="chartRetentionRate" height="120" style="margin-top:12px;"></canvas>
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
      <canvas id="chartProducts" height="280"></canvas>
      <details class="insight">
        <summary>Business Insight</summary>
        <div class="insight-body">{txt_products}</div>
      </details>
    </div>
  </div>
  <div id="city">
    <h2>🏙️ City Leaderboard</h2>
    <div class="chart-card">
      <canvas id="chartCity" height="280"></canvas>
      <details class="insight">
        <summary>Business Insight</summary>
        <div class="insight-body">{txt_city}</div>
      </details>
    </div>
  </div>
</div>

<!-- Top Customers by LTV -->
<div class="section" id="customers">
  <h2>💎 Top 10 Customers by Lifetime Value (RANK() over vw_customer_ltv)</h2>
  <div class="chart-card">
    <table>
      <thead><tr><th>Rank</th><th>Customer</th><th>Segment</th><th>City</th><th>Orders</th><th>Lifetime Revenue</th></tr></thead>
      <tbody>{customer_rows}</tbody>
    </table>
    <details class="insight">
      <summary>Business Insight</summary>
      <div class="insight-body">{txt_customers}</div>
    </details>
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
  Built with: SQLite · Python · Pandas · Chart.js · CTEs · Window Functions · Triggers · Cohort Analysis
</div>

<script src="https://cdn.jsdelivr.net/npm/chart.js@4.4.4/dist/chart.umd.min.js"></script>
<script>
{chart_script}

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
