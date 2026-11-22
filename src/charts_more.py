"""Charts for Act 2 (the experiment) and Act 3 (customer value)."""
import json
import numpy as np
import pandas as pd
from charts import plt, save, NAVY, AMBER, RED, GREEN, GREY, BLUE
from config import REPORTS

def act2(E):
    res = pd.DataFrame(E["results"]).set_index("arm"); cols = [GREY, RED, GREEN]; names = ["A: Control", "B: 10% off", "C: New page"]
    fig, ax = plt.subplots(1, 2, figsize=(14.5, 5.4))
    ax[0].bar(names, res.conversion_pct, color=cols, width=.55)
    for i, v in enumerate(res.conversion_pct): ax[0].text(i, v + .05, f"{v:.2f}%", ha="center", fontweight="bold")
    ax[0].set_ylim(0, res.conversion_pct.max() * 1.2)
    ax[0].set_title(f"Conversion (%)\nB p = {res.p['B']:.3f} (no) · C p = {res.p['C']:.3f} (yes, < 0.025)", fontsize=13)
    ax[1].bar(names, res.profit_per_visitor, color=cols, width=.55)
    for i, v in enumerate(res.profit_per_visitor): ax[1].text(i, v + .05, f"${v:.2f}", ha="center", fontweight="bold")
    for i, arm in ((1, "B"), (2, "C")):
        lo, hi = res.profit_ci[arm]; base = res.profit_per_visitor["A"]
        ax[1].errorbar(i + .33, base + (lo + hi) / 2, yerr=(hi - lo) / 2, fmt="o", color=NAVY, capsize=6)
    ax[1].set_ylim(0, res.profit_per_visitor.max() * 1.3)
    ax[1].set_title("Profit per visitor ($), with 97.5% intervals\nB: lower for sure · C: probably higher, not certain", fontsize=13)
    save(fig, "08_exp_results")

    pk = pd.DataFrame(E["peeking"]); pk["day"] = pd.to_datetime(pk.day)
    fig, ax = plt.subplots(figsize=(14.5, 5.4))
    ax.plot(pk.day, pk.p_B, color=RED, lw=2.5, label="B: 10% off"); ax.plot(pk.day, pk.p_C, color=GREEN, lw=2.5, label="C: new page")
    ax.axhline(0.025, color=NAVY, ls="--"); ax.text(pk.day.iloc[-1], 0.03, "  bar: 0.025", color=NAVY, va="bottom", ha="right")
    ax.set_yscale("log"); ax.set_ylim(0.002, 1); ax.legend(loc="upper right")
    low = pk.loc[pk.p_B.idxmin()]
    ax.annotate(f"Peek here and B 'wins'\n(p = {low.p_B:.3f})", (low.day, low.p_B), xytext=(low.day - pd.Timedelta(days=30), 0.004),
                arrowprops=dict(arrowstyle="->", color=RED), color=RED, fontsize=12)
    ax.set_title("The p-value you would have seen each day (log scale)")
    save(fig, "09_exp_peeking")

    dv = pd.DataFrame(E["by_device"])
    fig, ax = plt.subplots(figsize=(14.5, 5.0)); x = np.arange(2); w = .35
    for k, (arm, c) in enumerate((("B", RED), ("C", GREEN))):
        vals = [dv[(dv.device == d) & (dv.arm == arm)].lift_rel_pct.item() for d in ("mobile", "desktop")]
        ax.bar(x + (k - .5) * w, vals, w, color=c, label={"B": "B: 10% off", "C": "C: new page"}[arm])
        for i, v in enumerate(vals): ax.text(x[i] + (k - .5) * w, v + (0.6 if v >= 0 else -2.2), f"{v:+.1f}%", ha="center", fontweight="bold")
    ax.axhline(0, color="#333", lw=1); ax.set_xticks(x); ax.set_xticklabels(["Mobile (62% of visitors)", "Desktop"]); ax.legend()
    ax.set_title("Conversion lift vs control, by device: the new page works on mobile")
    save(fig, "10_exp_device")

def act3(C):
    curve = C["pareto"]["curve"]
    fig, ax = plt.subplots(figsize=(14.5, 5.2))
    ax.plot(np.linspace(0, 100, len(curve)), curve, color=NAVY, lw=3); ax.plot([0, 100], [0, 100], color=GREY, ls="--")
    ax.axvline(20, color=AMBER, lw=2); ax.text(30, 35, f"Top 20% of customers\n= {C['pareto']['top20_share']}% of profit", color="#92400e", fontsize=13)
    ax.set_xlabel("% of customers, most profitable first"); ax.set_ylabel("% of total profit"); ax.set_ylim(0, 105)
    ax.set_title("Who earns the profit? A few customers carry the business")
    save(fig, "11_pareto")

    s = pd.DataFrame(C["segments"]).set_index("segment")
    fig, ax = plt.subplots(figsize=(14.5, 5.4)); y = np.arange(len(s)); h = .38
    ax.barh(y - h / 2, s.pct_customers, h, color=GREY, label="% of customers"); ax.barh(y + h / 2, s.pct_profit, h, color=NAVY, label="% of profit")
    for i, (a, b) in enumerate(zip(s.pct_customers, s.pct_profit)):
        ax.text(a + .4, i - h / 2, f"{a:.0f}%", va="center", fontsize=11); ax.text(b + .4, i + h / 2, f"{b:.0f}%", va="center", fontsize=11, fontweight="bold")
    ax.set_yticks(y); ax.set_yticklabels(s.index); ax.invert_yaxis(); ax.legend(loc="lower right")
    ax.set_title("RFM segments: share of customers vs share of profit (to 31 Dec 2025)")
    save(fig, "12_segments")

    hd = pd.DataFrame(C["holdout"]).set_index("segment")
    fig, ax = plt.subplots(figsize=(14.5, 5.2))
    ax.bar(hd.index, hd.bought_again_pct, color=[GREEN, NAVY, AMBER, BLUE, GREY, RED], width=.6)
    for i, v in enumerate(hd.bought_again_pct): ax.text(i, v + 1, f"{v:.0f}%", ha="center", fontweight="bold")
    ax.set_ylim(0, hd.bought_again_pct.max() * 1.2)
    ax.set_title("Segments set on 30 Jun 2025: % who bought again, Jul to Dec")
    save(fig, "13_holdout")

    m = C["model"]
    fig, ax = plt.subplots(figsize=(14.5, 4.8))
    labs = ["Random pick", "Past profit", "RFM segments", "ML model"]; vals = [m["capture_random"], m["capture_past_profit"], m["capture_segment"], m["capture_model"]]
    ax.barh(labs, vals, color=[GREY, BLUE, NAVY, GREEN]); ax.invert_yaxis()
    for i, v in enumerate(vals): ax.text(v + .6, i, f"{v:.0f}%", va="center", fontweight="bold")
    ax.set_xlim(0, max(vals) * 1.2)
    ax.set_title("Target the top 20%: how much of next half-year's profit do you reach?")
    save(fig, "14_targeting")

    ch = pd.DataFrame(C["channels"]).set_index("acquisition_channel").loc[["Email & Referral", "Organic", "Paid Search", "Paid Social"]]
    fig, ax = plt.subplots(figsize=(14.5, 5.2)); x = np.arange(len(ch)); w = .36
    ax.bar(x - w / 2, ch.two_year_profit, w, color=NAVY, label="Profit per 2024 customer, over 2 years")
    ax.bar(x + w / 2, ch.spend_per_new_customer.fillna(0), w, color=RED, label="2025 spend per new customer")
    for i, (a, b) in enumerate(zip(ch.two_year_profit, ch.spend_per_new_customer)):
        ax.text(i - w / 2, a + 5, f"${a:.0f}", ha="center", fontweight="bold")
        ax.text(i + w / 2, (0 if pd.isna(b) else b) + 5, "free" if pd.isna(b) else f"${b:.0f}", ha="center", fontweight="bold", color=RED)
    ax.set_xticks(x); ax.set_xticklabels(ch.index); ax.legend(); ax.set_ylim(0, ch.two_year_profit.max() * 1.25)
    ax.set_title("Value by acquisition channel: Paid Social barely pays back")
    save(fig, "15_channels")

def main():
    print("Drawing Act 2 and Act 3 charts")
    act2(json.load(open(REPORTS / "experiment.json"))); act3(json.load(open(REPORTS / "customers.json")))
    print("  saved 8 charts")

if __name__ == "__main__":
    main()
