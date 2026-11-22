"""Step 3: the investigation. Runs the SQL in sql/analysis and turns it into answers.
Writes reports/findings.json, which the charts, report and memo all read from."""
import json, sqlite3
import numpy as np
import pandas as pd
from scipy import stats
from config import WAREHOUSE, SQL, REPORTS, RAW

con = sqlite3.connect(WAREHOUSE)
q = lambda name: pd.read_sql((SQL / "analysis" / name).read_text(), con)
sql = lambda s: pd.read_sql(s, con)

def naive_dashboard_revenue():
    """What a dashboard built straight on the raw exports reports (duplicates and test orders included)."""
    leg = pd.read_csv(RAW / "orders_legacy.csv")
    leg["year"] = pd.to_datetime(leg.order_ts_local, format="%m/%d/%Y %H:%M").dt.year
    new = json.load(open(RAW / "orders_new_platform.json"))
    rows = [dict(year=int(o["created_at"][:4]), v=i["qty"] * i["price"] * (1 - o["discount"])) for o in new for i in o["items"]]
    nv = pd.DataFrame(rows)
    by = (leg.assign(v=leg.quantity * leg.unit_price * (1 - leg.discount_pct)).groupby("year").v.sum()).add(nv.groupby("year").v.sum(), fill_value=0)
    return {int(k): round(float(v), 2) for k, v in by.items()}

def bridge(p, cat):
    """Contribution-profit bridge 2024 -> 2025. Each effect = 2025 actual minus 'what 2025 would have
    looked like at 2024 rates'. The pieces add up exactly to the change."""
    a, b = p.loc[2024], p.loc[2025]
    G24, G25 = a.gross_sales, b.gross_sales
    c24 = cat[cat.year == 2024].set_index("category"); c25 = cat[cat.year == 2025].set_index("category")
    cogs_rate24 = (c24.cogs_gross / c24.gross_sales)            # product cost per $ of gross sales, by category
    d24, s24 = a.discounts / G24, a.shipping / G24
    rc24 = (a.refunds - a.cogs_recovered) / G24                  # net cost of returns per $ of gross sales
    expected = (c25.gross_sales * (1 - cogs_rate24)).sum() - G25 * (d24 + rc24 + s24)
    volume = (G25 - G24) * (a.contribution_profit / G24)
    mix = expected - a.contribution_profit - volume
    discount = -(b.discounts - G25 * d24)
    returns = -((b.refunds - b.cogs_recovered) - G25 * rc24)
    shipping = -(b.shipping - G25 * s24)
    cost = -(c25.cogs_gross.sum() - (c25.gross_sales * cogs_rate24).sum())
    parts = dict(volume=volume, mix=mix, discounts=discount, returns=returns, shipping=shipping, product_cost=cost)
    assert abs(a.contribution_profit + sum(parts.values()) - b.contribution_profit) < 1, "bridge must add up"
    return {k: round(float(v)) for k, v in parts.items()}

def main():
    print("Investigating")
    F = {}
    p = sql("""SELECT year, SUM(gross_sales) gross_sales, SUM(discounts) discounts, SUM(net_sales) net_sales, SUM(refunds) refunds,
                      SUM(cogs) cogs, SUM(shipping) shipping, SUM(contribution_profit) contribution_profit, SUM(marketing) marketing, SUM(orders) orders
               FROM mart_monthly_pnl GROUP BY year""").set_index("year")
    rec = sql("SELECT CAST(SUBSTR(order_date,1,4) AS INT) year, SUM(cogs_recovered) cogs_recovered FROM fact_return GROUP BY 1").set_index("year")
    p["cogs_recovered"] = rec.cogs_recovered
    cat = sql("""SELECT CAST(SUBSTR(f.order_date,1,4) AS INT) year, d.category, SUM(f.gross_sales) gross_sales, SUM(f.cogs) cogs_gross
                 FROM fact_order_line f JOIN dim_product d ON d.sku = f.sku GROUP BY 1, 2""")
    F["pnl"] = {int(y): {k: round(float(v), 2) for k, v in r.items()} for y, r in p.iterrows()}
    F["growth"] = dict(net_sales_pct=round(100 * (p.loc[2025].net_sales / p.loc[2024].net_sales - 1), 1),
                       profit_pct=round(100 * (p.loc[2025].contribution_profit / p.loc[2024].contribution_profit - 1), 1))
    naive = naive_dashboard_revenue()
    F["naive_dashboard"] = dict(revenue=naive, growth_pct=round(100 * (naive[2025] / naive[2024] - 1), 1),
                                inflated_by=round(naive[2025] - float(p.loc[2025].net_sales)))
    F["bridge"] = bridge(p, cat)

    # Discounts: the sitewide promo
    d = q("a2_discounts_by_promo.sql"); F["discounts"] = d.to_dict("records")
    # A/B test
    ab = q("a5_ab_test.sql").set_index("test_group"); F["ab_test"] = ab.reset_index().to_dict("records")
    n1, x1, n2, x2 = ab.loc["Control", "customers"], ab.loc["Control", "buyers"], ab.loc["Treatment", "customers"], ab.loc["Treatment", "buyers"]
    pooled = (x1 + x2) / (n1 + n2); se = np.sqrt(pooled * (1 - pooled) * (1 / n1 + 1 / n2))
    z = (x2 / n2 - x1 / n1) / se; pval = 2 * (1 - stats.norm.cdf(abs(z)))
    per = sql("""SELECT a.customer_id, a.test_group, COALESCE(SUM(f.net_sales - f.cogs), 0) AS profit
                 FROM stg_ab_test a LEFT JOIN fact_order_line f ON f.customer_id = a.customer_id AND f.order_date BETWEEN '2025-09-01' AND '2025-09-30'
                 GROUP BY a.customer_id, a.test_group""")
    t = stats.ttest_ind(per[per.test_group == "Treatment"].profit, per[per.test_group == "Control"].profit, equal_var=False)
    diff = per[per.test_group == "Treatment"].profit.mean() - per[per.test_group == "Control"].profit.mean()
    se2 = np.sqrt(per[per.test_group == "Treatment"].profit.var() / n2 + per[per.test_group == "Control"].profit.var() / n1)
    F["ab_stats"] = dict(conv_control=round(100 * x1 / n1, 2), conv_treatment=round(100 * x2 / n2, 2), conv_lift_pts=round(100 * (x2 / n2 - x1 / n1), 2),
                         conv_z=round(float(z), 2), conv_p=round(float(pval), 3),
                         profit_diff_per_customer=round(float(diff), 2), profit_ci95=[round(float(diff - 1.96 * se2), 2), round(float(diff + 1.96 * se2), 2)],
                         profit_p=round(float(t.pvalue), 4))
    # Shipping: what SwiftShip heavy orders would have cost at ParcelPro's 2025 heavy rate
    s = q("a3_shipping_by_carrier.sql"); F["shipping"] = s.to_dict("records")
    sw = s[(s.year == 2025) & (s.carrier == "SwiftShip")].iloc[0]; pp = s[(s.year == 2025) & (s.carrier == "ParcelPro") & (s.weight_band.str.startswith("Heavy"))].iloc[0]
    F["shipping_extra"] = round(float(sw.orders * (sw.avg_cost_per_order - pp.avg_cost_per_order)))
    # Returns: the Aurora lamp
    r = q("a4_returns_by_product.sql"); F["returns_top_2025"] = r[r.year == 2025].head(5).to_dict("records")
    au = r[r.product_name == "Aurora Standing Lamp"].set_index("year")
    monthly_au = sql("""SELECT SUBSTR(r.order_date,1,7) month, SUM(r.quantity_returned) returned,
                        SUM(CASE WHEN reason LIKE 'Defective%' THEN quantity_returned ELSE 0 END) defective
                        FROM fact_return r JOIN dim_product p ON p.sku = r.sku WHERE p.product_name = 'Aurora Standing Lamp' GROUP BY 1""")
    sold_au = sql("""SELECT SUBSTR(f.order_date,1,7) month, SUM(f.quantity) sold FROM fact_order_line f JOIN dim_product p ON p.sku = f.sku
                     WHERE p.product_name = 'Aurora Standing Lamp' GROUP BY 1""")
    F["aurora"] = dict(by_year=au[["units_sold", "units_returned", "return_rate_pct", "defective_units", "return_cost"]].reset_index().to_dict("records"),
                       monthly=sold_au.merge(monthly_au, on="month", how="left").fillna(0).to_dict("records"))
    # Mix
    F["mix"] = q("a6_category_mix.sql").to_dict("records")
    # Cohorts
    co = q("a7_cohort_retention.sql"); F["cohorts"] = co.to_dict("records")
    # Duplicates found in cleaning
    F["cleaning_log"] = pd.read_csv(REPORTS.parent / "data" / "processed" / "cleaning_log.csv").to_dict("records")
    json.dump(F, open(REPORTS / "findings.json", "w"), indent=1, default=float)
    print("  growth", F["growth"], "| naive", F["naive_dashboard"]["growth_pct"], "| bridge", F["bridge"])
    print("  A/B", F["ab_stats"]); print("  shipping extra", F["shipping_extra"]); print("  aurora", F["aurora"]["by_year"])

if __name__ == "__main__":
    main()
