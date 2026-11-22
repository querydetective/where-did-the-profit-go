"""Act 3: which customers are worth keeping?
Customer value, RFM segments, a test of whether segments predict the next six months,
a simple model against that baseline, value by acquisition channel, and spend guidance.
Writes reports/customers.json and the warehouse table mart_customer_value."""
import json, sqlite3
import numpy as np
import pandas as pd
from sklearn.ensemble import GradientBoostingRegressor
from sklearn.metrics import mean_absolute_error
from config import WAREHOUSE, SQL, REPORTS

con = sqlite3.connect(WAREHOUSE)
SEGMENTS = ["Champions", "Loyal", "At risk", "New / promising", "Needs attention", "Hibernating"]

def segment(R, F):
    if R >= 4 and F >= 4: return "Champions"
    if R >= 3 and F >= 3: return "Loyal"
    if R >= 4 and F <= 2: return "New / promising"
    if R <= 2 and F >= 3: return "At risk"
    if R <= 2 and F <= 2: return "Hibernating"
    return "Needs attention"

def rfm(orders, asof):
    """Recency, frequency, monetary value for every customer who ordered on or before `asof`."""
    h = orders[orders.order_date <= asof]
    g = h.groupby("customer_id").agg(last_order=("order_date", "max"), first_order=("order_date", "min"),
                                     frequency=("order_id", "count"), monetary=("profit", "sum"))
    g["recency_days"] = (asof - g.last_order).dt.days
    g["tenure_days"] = (asof - g.first_order).dt.days
    g["R"] = pd.qcut(g.recency_days.rank(method="first"), 5, labels=[5, 4, 3, 2, 1]).astype(int)   # 5 = most recent
    g["F"] = pd.cut(g.frequency, [0, 1, 2, 3, 5, 999], labels=[1, 2, 3, 4, 5]).astype(int)        # 1, 2, 3, 4-5, 6+ orders
    g["M"] = pd.qcut(g.monetary.rank(method="first"), 5, labels=[1, 2, 3, 4, 5]).astype(int)
    g["segment"] = [segment(r, f) for r, f in zip(g.R, g.F)]
    return g

def main():
    print("Valuing customers")
    orders = pd.read_sql((SQL / "analysis" / "a8_order_profit.sql").read_text(), con, parse_dates=["order_date"])
    cust = pd.read_sql("SELECT customer_id, acquisition_channel, signup_date FROM dim_customer", con)
    C = {}

    # 1. Who earns the profit? (Pareto)
    total = orders.groupby("customer_id").profit.sum().sort_values(ascending=False)
    n = len(total)
    C["pareto"] = dict(buyers=n, total_profit=round(float(total.sum())),
                       top20_share=round(100 * total.head(int(n * .2)).sum() / total.sum(), 1),
                       top50_share=round(100 * total.head(int(n * .5)).sum() / total.sum(), 1),
                       unprofitable=int((total < 0).sum()), unprofitable_total=round(float(total[total < 0].sum())),
                       curve=[round(100 * float(x), 2) for x in (total.cumsum() / total.sum()).iloc[np.linspace(0, n - 1, 101).astype(int)]])

    # 2. Segments today (as of 31 Dec 2025)
    now = rfm(orders, pd.Timestamp("2025-12-31"))
    seg = now.groupby("segment").agg(customers=("frequency", "size"), avg_orders=("frequency", "mean"),
                                     avg_profit=("monetary", "mean"), profit=("monetary", "sum"), avg_recency_days=("recency_days", "mean"))
    seg["pct_customers"] = 100 * seg.customers / seg.customers.sum(); seg["pct_profit"] = 100 * seg.profit / seg.profit.sum()
    C["segments"] = seg.reindex(SEGMENTS).round(1).reset_index().to_dict("records")

    # 3. Do segments predict? Segment as of 30 Jun 2025, watch Jul-Dec 2025
    mid = pd.Timestamp("2025-06-30")
    past = rfm(orders, mid)
    fut = orders[orders.order_date > mid].groupby("customer_id").agg(next_orders=("order_id", "count"), next_profit=("profit", "sum"))
    past = past.join(fut).fillna({"next_orders": 0, "next_profit": 0})
    hold = past.groupby("segment").agg(customers=("frequency", "size"), bought_again_pct=("next_orders", lambda x: 100 * (x > 0).mean()),
                                       next6m_profit=("next_profit", "mean"))
    C["holdout"] = hold.reindex(SEGMENTS).round(1).reset_index().to_dict("records")

    # 4. A simple model vs the segment baseline (predict Jul-Dec profit from what we knew on 30 Jun)
    X = past[["recency_days", "frequency", "monetary", "tenure_days"]].join(
        pd.get_dummies(cust.set_index("customer_id").acquisition_channel, dtype=float), how="left").fillna(0)
    y = past.next_profit
    rng = np.random.default_rng(7); test = rng.random(len(X)) < 0.3
    base_pred = past[~test].groupby("segment").next_profit.mean().reindex(past[test].segment).values
    model = GradientBoostingRegressor(random_state=7, max_depth=3, n_estimators=200, learning_rate=0.05).fit(X[~test], y[~test])
    pred = model.predict(X[test])
    yt = y[test].values
    def capture(score):                                   # share of future profit held by the top 20% we would target
        top = np.argsort(-np.asarray(score))[: int(len(score) * .2)]
        return round(100 * yt[top].sum() / yt.sum(), 1)
    seg_rank = past[test].segment.map(past[~test].groupby("segment").next_profit.mean()).values + 1e-6 * past[test].monetary.values
    imp = pd.Series(model.feature_importances_, index=X.columns).sort_values(ascending=False)
    C["model"] = dict(train=int((~test).sum()), test=int(test.sum()),
                      mae_zero=round(float(mean_absolute_error(y[test], np.zeros(test.sum()))), 2),
                      mae_segment=round(float(mean_absolute_error(y[test], base_pred)), 2),
                      mae_model=round(float(mean_absolute_error(y[test], pred)), 2),
                      capture_random=20.0, capture_segment=capture(seg_rank), capture_model=capture(pred),
                      capture_past_profit=capture(past[test].monetary.values),
                      importance={k: round(float(v), 3) for k, v in imp.head(5).items()})

    # 5. Expected next-12-month profit per customer, by segment (2 x observed 6-month profit) and spend guidance
    exp12 = (2 * hold.next6m_profit).reindex(SEGMENTS)
    plan = pd.DataFrame({"customers_now": seg.customers.reindex(SEGMENTS), "expected_12m_profit": exp12.round(0)})
    plan["max_spend_per_customer"] = (0.3 * plan.expected_12m_profit).round(0)          # keep 70% of expected profit
    plan["action"] = ["Thank, early access, no discounts", "Cross-sell, loyalty perks", "Win-back offer, one email series",
                      "Second-order welcome series", "Light-touch reminders", "Cheap channels only, or none"]
    C["plan"] = plan.reset_index().rename(columns={"index": "segment"}).to_dict("records")

    # 6. Value by acquisition channel (2024 sign-ups: two full years to watch) + 2025 spend per new customer
    tot = total.rename("profit")
    c24 = cust[cust.signup_date.str.startswith("2024")].merge(tot, left_on="customer_id", right_index=True, how="left").fillna({"profit": 0})
    ch = c24.groupby("acquisition_channel").agg(customers=("profit", "size"), two_year_profit=("profit", "mean"))
    mk = pd.read_sql("SELECT channel, SUM(spend) AS spend FROM stg_marketing WHERE month LIKE '2025%' GROUP BY channel", con).set_index("channel").spend
    new25 = cust[cust.signup_date.str.startswith("2025")].groupby("acquisition_channel").size()
    ch["new_customers_2025"] = new25; ch["spend_2025"] = mk; ch["spend_per_new_customer"] = (mk / new25).round(2)
    C["channels"] = ch.round(1).reset_index().to_dict("records")

    # 7. The weak 2025-Q3 cohort: who were they?
    first = orders.sort_values("order_date").groupby("customer_id").head(1)
    q3 = first[first.order_date.dt.to_period("Q") == "2025Q3"]
    ab = set(pd.read_sql("SELECT customer_id FROM stg_ab_test", con).customer_id)
    q4buyers = set(orders[orders.order_date.dt.to_period("Q") == "2025Q4"].customer_id)
    is_test = q3.customer_id.isin(ab) & (q3.order_date.dt.month == 9)
    C["q3_cohort"] = dict(customers=len(q3), from_test=int(is_test.sum()),
                          back_pct_test=round(100 * q3[is_test].customer_id.isin(q4buyers).mean(), 1),
                          back_pct_other=round(100 * q3[~is_test].customer_id.isin(q4buyers).mean(), 1))

    out = now.join(cust.set_index("customer_id"))[["acquisition_channel", "frequency", "recency_days", "monetary", "R", "F", "M", "segment"]]
    out.rename(columns={"monetary": "profit_to_date"}).reset_index().to_sql("mart_customer_value", con, if_exists="replace", index=False)
    json.dump(C, open(REPORTS / "customers.json", "w"), indent=1, default=float)
    print("  pareto", {k: C["pareto"][k] for k in ("buyers", "top20_share", "unprofitable")}, "| model", {k: C["model"][k] for k in ("mae_zero", "mae_segment", "mae_model")})

if __name__ == "__main__":
    main()
