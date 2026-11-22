"""Act 2 raw data: the follow-up website experiment, 12 Jan - 26 Apr 2026 (15 weeks).

Exported by the experimentation platform, one row per visitor. Three arms:
  A  control (no offer)
  B  10% off sitewide banner
  C  new product page: delivery date and reviews near the Add to Cart button
Like every real export it has problems: some visitors landed in two arms (cookie resets),
and bot traffic crawled the new page. Seeded, so everyone gets identical files.
"""
from datetime import datetime, timedelta
import numpy as np
import pandas as pd
from config import RAW

rng = np.random.default_rng(2026)
START, DAYS = datetime(2026, 1, 12), 105
products = pd.read_excel(RAW / "products.xlsx", sheet_name="catalog")
MIX = {"Textiles": .25, "Kitchen": .23, "Furniture": .14, "Lighting": .14, "Smart Home": .24}
by_cat = {c: products[products.category == c].reset_index(drop=True) for c in MIX}

BASE = {"mobile": 0.026, "desktop": 0.036}                     # conversion without any change
LIFT = {"A": {"mobile": 1.00, "desktop": 1.00},
        "B": {"mobile": 1.05, "desktop": 1.05},                # 10% off: small lift ...
        "C": {"mobile": 1.24, "desktop": 1.05}}                # new page: helps mobile most
NOVELTY_B = 1.30                                               # ... but a big first-week spike for the banner

def basket():
    n = int(rng.choice([1, 1, 1, 2, 2, 3])); gross = cogs = kg = 0.0
    for _ in range(n):
        cat = str(rng.choice(list(MIX), p=list(MIX.values())))
        p = by_cat[cat].iloc[int(rng.integers(len(by_cat[cat])))]
        q = int(rng.choice([1, 1, 1, 2]))
        gross += q * p.list_price; cogs += q * p.unit_cost; kg += q * p.weight_kg
    ship = 9.0 + 1.75 * kg if kg > 10 else 6.0 + 0.85 * kg
    return gross, cogs, round(ship * float(rng.uniform(.97, 1.03)), 2)

rows = []; vid = 700000
for day in range(DAYS):
    d = START + timedelta(days=day)
    for _ in range(rng.poisson(830 * (1.12 if d.weekday() >= 5 else 1.0))):
        vid += 1
        arm = str(rng.choice(["A", "B", "C"]))
        dev = "mobile" if rng.random() < 0.62 else "desktop"
        vtype = "returning" if rng.random() < 0.35 else "new"
        p = BASE[dev] * LIFT[arm][dev] * (1.35 if vtype == "returning" else 1.0)
        if arm == "B" and day < 7: p *= NOVELTY_B / LIFT["B"][dev]
        row = dict(visitor_id=f"V{vid}", arm=arm, first_seen=(d + timedelta(minutes=int(rng.integers(0, 1440)))).strftime("%Y-%m-%d %H:%M"),
                   device=dev, visitor_type=vtype, pageviews=int(rng.integers(1, 12)), seconds_on_site=int(rng.gamma(2, 90)),
                   ordered=0, gross_sales=0.0, discount=0.0, cogs=0.0, ship_cost=0.0, refund=0.0, cogs_recovered=0.0)
        if rng.random() < p:
            g, c, s = basket()
            disc = round(g * 0.10, 2) if arm == "B" else 0.0
            row.update(ordered=1, gross_sales=round(g, 2), discount=disc, cogs=round(c, 2), ship_cost=s)
            if rng.random() < (0.055 if arm == "C" else 0.065):                     # clearer delivery info: fewer returns
                row.update(refund=round(g - disc, 2), cogs_recovered=round(c, 2))
        rows.append(row)
visits = pd.DataFrame(rows)

# Problem 1: cookie resets put some visitors in a second arm
dup = visits.sample(900, random_state=3).copy()
dup["arm"] = [str(rng.choice([a for a in "ABC" if a != x])) for x in dup.arm]
dup[["ordered", "gross_sales", "discount", "cogs", "ship_cost", "refund", "cogs_recovered"]] = 0
# Problem 2: a crawler hit the new product page thousands of times
bots = pd.DataFrame(dict(visitor_id=[f"BOT{i}" for i in range(2400)], arm="C",
                         first_seen=[(START + timedelta(days=int(rng.integers(0, DAYS)), minutes=int(rng.integers(0, 1440)))).strftime("%Y-%m-%d %H:%M") for _ in range(2400)],
                         device="desktop", visitor_type="new", pageviews=rng.integers(60, 400, 2400), seconds_on_site=0,
                         ordered=0, gross_sales=0.0, discount=0.0, cogs=0.0, ship_cost=0.0, refund=0.0, cogs_recovered=0.0))
out = pd.concat([visits, dup, bots]).sample(frac=1, random_state=5).reset_index(drop=True)
out.to_csv(RAW / "experiment_visits.csv", index=False)
print("experiment visitors", len(visits), "+", len(dup), "duplicates +", len(bots), "bots")
