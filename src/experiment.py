"""Act 2: the follow-up experiment, analyzed the way a decision needs.
Plan the sample size, clean the export, check the split, measure conversion AND profit,
watch a guardrail, look by device, show why peeking misleads, and make the call.
Writes reports/experiment.json and the warehouse table stg_experiment."""
import json, sqlite3
import numpy as np
import pandas as pd
from scipy import stats
from config import RAW, WAREHOUSE, REPORTS

ARMS = {"A": "Control", "B": "10% off banner", "C": "New product page"}

def sample_size(p, rel_lift, alpha=0.05, power=0.80, comparisons=1):
    """Visitors per arm to detect a relative lift in a conversion rate (two-sided z-test, Bonferroni)."""
    za = stats.norm.ppf(1 - alpha / (2 * comparisons)); zb = stats.norm.ppf(power)
    d = p * rel_lift; pbar = p + d / 2
    return int(np.ceil((za + zb) ** 2 * 2 * pbar * (1 - pbar) / d ** 2))

def ztest(x1, n1, x2, n2):
    p1, p2 = x1 / n1, x2 / n2; pool = (x1 + x2) / (n1 + n2)
    z = (p2 - p1) / np.sqrt(pool * (1 - pool) * (1 / n1 + 1 / n2))
    return float(z), float(2 * (1 - stats.norm.cdf(abs(z))))

def diff_ci(a, b, alpha):
    d = b.mean() - a.mean(); se = np.sqrt(a.var() / len(a) + b.var() / len(b)); z = stats.norm.ppf(1 - alpha / 2)
    return round(float(d), 3), [round(float(d - z * se), 3), round(float(d + z * se), 3)]

def main():
    print("Analyzing the experiment")
    E = {"plan": dict(baseline_conversion_pct=3.0, min_lift_pct=15, alpha=0.05, power=0.8, comparisons=2,
                      visitors_per_arm=sample_size(0.03, 0.15, comparisons=2), visitors_per_arm_single=sample_size(0.03, 0.15))}
    raw = pd.read_csv(RAW / "experiment_visits.csv")
    E["raw_counts"] = raw.arm.value_counts().sort_index().to_dict()
    chi_raw = stats.chisquare(raw.arm.value_counts().sort_index().values)
    # Clean: bots, then visitors seen in more than one arm
    bot = (raw.pageviews >= 60) & (raw.seconds_on_site == 0)
    multi = raw[~bot].groupby("visitor_id").arm.nunique()
    multi_ids = set(multi[multi > 1].index)
    v = raw[~bot & ~raw.visitor_id.isin(multi_ids)].copy()
    E["cleaning"] = dict(raw_rows=len(raw), bots=int(bot.sum()), multi_arm_visitors=len(multi_ids),
                         multi_arm_rows=int(raw[~bot].visitor_id.isin(multi_ids).sum()), clean_visitors=len(v))
    counts = v.arm.value_counts().sort_index()
    E["srm"] = dict(raw_p=float(chi_raw.pvalue), clean_counts=counts.to_dict(), clean_p=round(float(stats.chisquare(counts.values).pvalue), 3))
    E["balance"] = (v.groupby("arm").agg(mobile_pct=("device", lambda x: 100 * (x == "mobile").mean()),
                                        returning_pct=("visitor_type", lambda x: 100 * (x == "returning").mean())).round(1).to_dict("index"))
    v["net_sales"] = v.gross_sales - v.discount
    v["profit"] = v.net_sales - v.refund - (v.cogs - v.cogs_recovered) - v.ship_cost
    v["day"] = pd.to_datetime(v.first_seen).dt.normalize()
    alpha = 0.05 / 2
    res = []
    A = v[v.arm == "A"]
    for arm in "ABC":
        g = v[v.arm == arm]; buyers = g[g.ordered == 1]
        r = dict(arm=arm, name=ARMS[arm], visitors=len(g), orders=int(g.ordered.sum()), conversion_pct=round(100 * g.ordered.mean(), 2),
                 avg_order_net=round(float(buyers.net_sales.mean()), 2), return_rate_pct=round(100 * (buyers.refund > 0).mean(), 2),
                 profit_per_visitor=round(float(g.profit.mean()), 3), total_profit=round(float(g.profit.sum())))
        if arm != "A":
            z, p = ztest(A.ordered.sum(), len(A), g.ordered.sum(), len(g))
            r.update(conv_lift_pts=round(100 * (g.ordered.mean() - A.ordered.mean()), 2), conv_lift_rel_pct=round(100 * (g.ordered.mean() / A.ordered.mean() - 1), 1),
                     z=round(z, 2), p=round(p, 4), significant=bool(p < alpha))
            r["profit_diff_per_visitor"], r["profit_ci"] = diff_ci(A.profit, g.profit, alpha)
            r["return_z_p"] = round(ztest((A[A.ordered == 1].refund > 0).sum(), A.ordered.sum(), (buyers.refund > 0).sum(), len(buyers))[1], 3)
        res.append(r)
    E["results"] = res
    # By device
    dev = []
    for d_ in ("mobile", "desktop"):
        a = v[(v.arm == "A") & (v.device == d_)]
        for arm in "BC":
            g = v[(v.arm == arm) & (v.device == d_)]
            z, p = ztest(a.ordered.sum(), len(a), g.ordered.sum(), len(g))
            dev.append(dict(device=d_, arm=arm, control_pct=round(100 * a.ordered.mean(), 2), arm_pct=round(100 * g.ordered.mean(), 2),
                            lift_rel_pct=round(100 * (g.ordered.mean() / a.ordered.mean() - 1), 1), p=round(p, 4)))
    E["by_device"] = dev
    # Peeking: the p-value you would have seen each day
    peek = []
    for day in sorted(v.day.unique()):
        s = v[v.day <= day]; a = s[s.arm == "A"]; row = dict(day=str(pd.Timestamp(day).date()))
        for arm in "BC":
            g = s[s.arm == arm]; row[f"p_{arm}"] = round(ztest(a.ordered.sum(), len(a), g.ordered.sum(), len(g))[1], 4)
            row[f"lift_{arm}"] = round(100 * (g.ordered.mean() / a.ordered.mean() - 1), 1)
        peek.append(row)
    E["peeking"] = peek
    wk = v.assign(week=((v.day - v.day.min()).dt.days // 7) + 1).groupby(["week", "arm"]).ordered.mean().unstack() * 100
    E["weekly_conversion"] = wk.round(2).reset_index().to_dict("records")
    # Annualized value of shipping C to everyone, at the test's per-visitor difference
    c = next(r for r in res if r["arm"] == "C"); b = next(r for r in res if r["arm"] == "B")
    visitors_per_year = len(v) / 105 * 365
    E["annual"] = dict(visitors_per_year=round(visitors_per_year), C_profit=round(c["profit_diff_per_visitor"] * visitors_per_year),
                       C_low=round(c["profit_ci"][0] * visitors_per_year), C_high=round(c["profit_ci"][1] * visitors_per_year),
                       B_profit=round(b["profit_diff_per_visitor"] * visitors_per_year))
    con = sqlite3.connect(WAREHOUSE); v.drop(columns="day").to_sql("stg_experiment", con, if_exists="replace", index=False); con.close()
    json.dump(E, open(REPORTS / "experiment.json", "w"), indent=1, default=float)
    for r in res: print("  ", {k: r[k] for k in r if k in ("arm", "visitors", "conversion_pct", "profit_per_visitor", "p", "profit_ci")})

if __name__ == "__main__":
    main()
