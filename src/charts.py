"""Step 4: charts for the report and dashboard (reports/charts/*.png)."""
import json, sqlite3
import matplotlib; matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.ticker as mt
import numpy as np
import pandas as pd
from config import WAREHOUSE, REPORTS

NAVY, AMBER, RED, GREEN, GREY, BLUE = "#1e3a5f", "#f59e0b", "#dc2626", "#16a34a", "#94a3b8", "#3b82f6"
plt.rcParams.update({"font.family": "DejaVu Sans", "font.size": 13, "axes.spines.top": False, "axes.spines.right": False,
                     "axes.titleweight": "bold", "axes.titlesize": 17, "axes.titlelocation": "left", "figure.dpi": 100})
OUT = REPORTS / "charts"
money = mt.FuncFormatter(lambda v, _: f"${v/1000:,.0f}K")

def save(fig, name):
    fig.tight_layout(); fig.savefig(OUT / f"{name}.png", dpi=110); plt.close(fig)

def main():
    print("Drawing charts")
    F = json.load(open(REPORTS / "findings.json")); con = sqlite3.connect(WAREHOUSE)
    m = pd.read_sql("SELECT * FROM mart_monthly_pnl", con); m["mon"] = m.month.str[5:].astype(int)
    # 1 monthly sales vs profit
    fig, ax = plt.subplots(1, 2, figsize=(14.5, 5.4), sharex=True)
    for y, c, ls in ((2024, GREY, "-"), (2025, NAVY, "-")):
        d = m[m.year == y]
        ax[0].plot(d.mon, d.net_sales, color=c, lw=3, label=str(y)); ax[1].plot(d.mon, d.contribution_profit, color=c, lw=3, label=str(y))
    ax[0].set_title("Net sales by month"); ax[1].set_title("Contribution profit by month")
    for a in ax:
        a.yaxis.set_major_formatter(money); a.set_xticks(range(1, 13)); a.set_xticklabels(list("JFMAMJJASOND")); a.legend(frameon=False); a.grid(axis="y", alpha=.25)
    ax[1].axvspan(9.5, 12.5, color=AMBER, alpha=.15); ax[1].text(9.7, ax[1].get_ylim()[1] * .93, "20% off sitewide", color="#92400e", fontsize=11)
    save(fig, "01_sales_vs_profit")
    # 2 bridge waterfall
    b = F["bridge"]; p = F["pnl"]
    steps = [("2024 profit", p["2024"]["contribution_profit"], "total"), ("More volume", b["volume"], ""), ("Discounts", b["discounts"], ""),
             ("Sales mix", b["mix"], ""), ("Shipping", b["shipping"], ""), ("Returns", b["returns"], ""), ("Product cost", b["product_cost"], ""),
             ("2025 profit", p["2025"]["contribution_profit"], "total")]
    fig, ax = plt.subplots(figsize=(14.5, 6.2)); run = 0
    for i, (lab, v, kind) in enumerate(steps):
        if kind == "total":
            ax.bar(i, v, color=NAVY, width=.62); run = v; top = v
        else:
            ax.bar(i, v, bottom=run, color=GREEN if v >= 0 else RED, width=.62); top = max(run, run + v); run += v
        ax.text(i, top + 12000, (f"${v/1000:,.0f}K" if kind else f"{'+' if v >= 0 else '−'}${abs(v)/1000:,.0f}K"), ha="center", fontsize=12, fontweight="bold")
    ax.set_xticks(range(len(steps))); ax.set_xticklabels([s[0] for s in steps]); ax.yaxis.set_major_formatter(money)
    ax.set_ylim(0, max(p["2024"]["contribution_profit"], p["2024"]["contribution_profit"] + b["volume"]) * 1.12)
    ax.set_title("Where the profit went: 2024 to 2025 contribution profit bridge"); ax.grid(axis="y", alpha=.25)
    save(fig, "02_profit_bridge")
    # 3 A/B test
    ab = pd.DataFrame(F["ab_test"]).set_index("test_group"); s = F["ab_stats"]
    fig, ax = plt.subplots(1, 2, figsize=(14.5, 5.2))
    ax[0].bar(["Control", "20% off"], ab.conversion_pct, color=[GREY, AMBER], width=.55); 
    for i, v in enumerate(ab.conversion_pct): ax[0].text(i, v + .2, f"{v:.2f}%", ha="center", fontweight="bold")
    ax[0].set_title(f"Conversion (%)\n+{s['conv_lift_pts']} pts, p = {s['conv_p']}: not significant", fontsize=13); ax[0].set_ylim(0, max(ab.conversion_pct) * 1.18)
    ax[1].bar(["Control", "20% off"], ab.product_profit_per_customer, color=[GREY, RED], width=.55); 
    for i, v in enumerate(ab.product_profit_per_customer): ax[1].text(i, v + .3, f"${v:.2f}", ha="center", fontweight="bold")
    ax[1].set_title(f"Product profit per customer ($)\n{s['profit_diff_per_customer']:+.2f}, 95% CI {s['profit_ci95'][0]} to {s['profit_ci95'][1]}", fontsize=13); ax[1].set_ylim(0, max(ab.product_profit_per_customer) * 1.18)
    for a in ax: a.grid(axis="y", alpha=.25)
    save(fig, "03_ab_test")
    # 4 shipping
    sh = pd.read_sql("""SELECT SUBSTR(order_date,1,7) month, AVG(ship_cost) avg_cost FROM fact_shipment WHERE billed_weight_kg > 10 GROUP BY 1""", con)
    fig, ax = plt.subplots(figsize=(14.5, 5.2)); ax.plot(range(len(sh)), sh.avg_cost, color=NAVY, lw=3, marker="o")
    ax.axvline(14.5, color=RED, ls="--"); ax.text(14.7, sh.avg_cost.max() * .55, "April 2025:\nheavy orders move\nto SwiftShip", color=RED, fontsize=12)
    ax.set_xticks(range(0, len(sh), 3)); ax.set_xticklabels(sh.month[::3]); ax.yaxis.set_major_formatter(mt.FuncFormatter(lambda v, _: f"${v:.0f}"))
    ax.set_title("Average shipping cost per heavy order (>10 kg)"); ax.grid(axis="y", alpha=.25); ax.set_ylim(0, sh.avg_cost.max() * 1.15)
    save(fig, "04_shipping")
    # 5 Aurora returns
    au = pd.DataFrame(F["aurora"]["monthly"]); au["rate"] = 100 * au.returned / au.sold
    fig, ax = plt.subplots(figsize=(14.5, 5.2)); ax.bar(range(len(au)), au.rate, color=[RED if 45 <= r or (m >= "2025-05" and m <= "2025-10") else GREY for r, m in zip(au.rate, au.month)])
    ax.set_xticks(range(0, len(au), 3)); ax.set_xticklabels(au.month[::3]); ax.set_title("Aurora Standing Lamp: return rate by month of sale (%)"); ax.grid(axis="y", alpha=.25)
    ax.set_title("Aurora Standing Lamp: return rate by month of sale. Red = May to Oct 2025, 'Defective - flickering'")
    save(fig, "05_aurora_returns")
    # 6 mix
    mx = pd.DataFrame(F["mix"]); cats = ["Textiles", "Lighting", "Kitchen", "Furniture", "Smart Home"]; cols = [GREEN, "#84cc16", BLUE, NAVY, RED]
    fig, ax = plt.subplots(figsize=(14.5, 5.4)); left = {2024: 0, 2025: 0}
    for cat, c in zip(cats, cols):
        for yi, y in enumerate((2024, 2025)):
            r = mx[(mx.year == y) & (mx.category == cat)].iloc[0]
            ax.barh(yi, r.share_pct, left=left[y], color=c); ax.text(left[y] + r.share_pct / 2, yi, f"{cat}\n{r.share_pct:.0f}%", ha="center", va="center", color="white", fontsize=11, fontweight="bold")
            left[y] += r.share_pct
    ax.set_yticks([0, 1]); ax.set_yticklabels(["2024", "2025"]); ax.set_xlim(0, 100); ax.invert_yaxis(); ax.set_xticks([])
    sh24 = mx[(mx.year == 2024) & (mx.category == "Smart Home")].share_pct.item(); sh25 = mx[(mx.year == 2025) & (mx.category == "Smart Home")].share_pct.item()
    ax.set_title(f"Sales mix: Smart Home (about 20% product margin) grew from {sh24:.0f}% to {sh25:.0f}% of sales")
    save(fig, "06_mix")
    # 7 cohorts
    co = pd.DataFrame(F["cohorts"]); hm = co.pivot(index="cohort", columns="q_after", values="pct_of_cohort").iloc[:, 1:7].dropna(how="all")
    fig, ax = plt.subplots(figsize=(14.5, 5.6)); im = ax.imshow(hm.values, cmap="Blues", vmin=0, vmax=40, aspect="auto")
    for i in range(hm.shape[0]):
        for j in range(hm.shape[1]):
            v = hm.values[i, j]
            if not np.isnan(v): ax.text(j, i, f"{v:.0f}%", ha="center", va="center", color="white" if v > 25 else NAVY, fontsize=11)
    ax.set_xticks(range(hm.shape[1])); ax.set_xticklabels([f"+{c} qtr" for c in hm.columns]); ax.set_yticks(range(len(hm))); ax.set_yticklabels(hm.index)
    ax.set_title("Cohort retention: % of each first-order quarter who ordered again"); ax.spines[:].set_visible(False)
    save(fig, "07_cohorts")
    print("  saved 7 charts")

if __name__ == "__main__":
    main()
