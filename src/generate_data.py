"""Generate the Harbor & Hearth raw data (2024-2025).

This script exists so the project is fully reproducible. In a real job you would
receive these files from source systems; here we create them, with the same kinds
of problems real exports have. Seeded, so everyone gets identical files.
"""
import json, random
from datetime import date, datetime, timedelta
from pathlib import Path
import numpy as np
import pandas as pd

RAW = Path(__file__).resolve().parents[1] / "data" / "raw"
RAW.mkdir(parents=True, exist_ok=True)
rng = np.random.default_rng(2025); random.seed(2025)

# ---------------------------------------------------------------- products
CATS = {  # category: (count, price range, cost ratio, weight range kg)
    "Textiles":   (14, (25, 95), 0.35, (0.8, 3.0)),
    "Kitchen":    (12, (20, 160), 0.45, (0.8, 6.0)),
    "Furniture":  (10, (160, 620), 0.55, (12.0, 38.0)),
    "Lighting":   (10, (40, 230), 0.45, (2.0, 9.0)),
    "Smart Home": (10, (40, 260), 0.80, (0.4, 3.0)),
}
NAMES = {
    "Textiles": ["Linen Throw", "Wool Blanket", "Cotton Pillow", "Bath Towel Set", "Velvet Cushion", "Quilted Bedspread", "Table Runner", "Waffle Robe", "Jute Rug", "Sherpa Throw", "Duvet Cover", "Hand Towels", "Knit Pouf Cover", "Tea Towels"],
    "Kitchen": ["Cast Iron Skillet", "Ceramic Mug Set", "Chef Knife", "Pour-Over Kettle", "Stoneware Bowls", "Bamboo Board", "Dutch Oven", "Glass Storage Set", "Copper Measuring Cups", "Salad Bowl", "Spice Rack", "French Press"],
    "Furniture": ["Oak Side Table", "Accent Chair", "Walnut Bookshelf", "Storage Bench", "Bar Stool", "Console Table", "Nesting Tables", "Coffee Table", "Rattan Lounger", "Writing Desk"],
    "Lighting": ["Brass Table Lamp", "Pendant Light", "String Lights", "Desk Lamp", "Wall Sconce", "Floor Lamp", "Aurora Standing Lamp", "Candle Lantern", "Reading Light", "Globe Lamp"],
    "Smart Home": ["Smart Plug 4-Pack", "Video Doorbell", "Smart Thermostat", "Wi-Fi Camera", "Smart Bulb Kit", "Smart Speaker", "Motion Sensor Kit", "Smart Lock", "Robot Vacuum", "Air Quality Monitor"],
}
CODES = {"Textiles": "TEX", "Kitchen": "KIT", "Furniture": "FUR", "Lighting": "LGT", "Smart Home": "SMH"}
prods = []
for cat, (n, (lo, hi), cr, (wl, wh)) in CATS.items():
    for i in range(n):
        price = round(float(rng.uniform(lo, hi)) / 5) * 5 - 0.01
        prods.append(dict(sku=f"HH-{CODES[cat]}-{i+1:03d}", product_name=NAMES[cat][i], category=cat,
                          list_price=round(price, 2), unit_cost=round(price * cr * float(rng.uniform(0.92, 1.08)), 2),
                          weight_kg=round(float(rng.uniform(wl, wh)), 1)))
products = pd.DataFrame(prods)
AURORA = products.loc[products.product_name == "Aurora Standing Lamp", "sku"].item()
products.loc[products.sku == AURORA, ["list_price", "weight_kg"]] = [189.99, 8.5]
products.loc[products.sku == AURORA, "unit_cost"] = round(189.99 * 0.45, 2)

# ---------------------------------------------------------------- customers
CHANNELS = ["Organic", "Paid Search", "Paid Social", "Email & Referral"]
STATES = ["NJ", "NY", "PA", "CA", "TX", "FL", "IL", "MA", "WA", "GA", "NC", "OH"]
cust = []; cid = 10000
def new_customers(start, end, n, chan_p):
    global cid
    days = (end - start).days
    for _ in range(n):
        cid += 1
        cust.append(dict(customer_id=f"C{cid}", signup_date=start + timedelta(days=int(rng.integers(0, days))),
                         state=str(rng.choice(STATES)), acquisition_channel=str(rng.choice(CHANNELS, p=chan_p))))
new_customers(date(2022, 1, 1), date(2024, 1, 1), 4200, [0.35, 0.30, 0.15, 0.20])
new_customers(date(2024, 1, 1), date(2025, 1, 1), 2600, [0.33, 0.29, 0.20, 0.18])
new_customers(date(2025, 1, 1), date(2026, 1, 1), 3400, [0.28, 0.27, 0.30, 0.15])
customers = pd.DataFrame(cust)

# ---------------------------------------------------------------- order simulation
mix24 = {"Textiles": .31, "Kitchen": .25, "Furniture": .14, "Lighting": .15, "Smart Home": .15}
mix25 = {"Textiles": .25, "Kitchen": .23, "Furniture": .14, "Lighting": .14, "Smart Home": .24}
season = {1: .80, 2: .78, 3: .90, 4: .92, 5: .97, 6: .95, 7: .93, 8: .95, 9: 1.0, 10: 1.05, 11: 1.35, 12: 1.55}
by_cat = {c: products[products.category == c].reset_index(drop=True) for c in CATS}

HOURS = np.array([1,1,1,1,1,1,2,3,4,5,6,6,6,6,6,6,6,7,8,9,9,8,5,2], float); HOURS /= HOURS.sum()
SIGN = pd.to_datetime(customers.signup_date).values
# Customers differ: some buy often, some rarely, and many drift away. A separate generator
# keeps every other random draw (orders, items, discounts, returns) exactly as before.
rng2 = np.random.default_rng(11)
CH_MULT = {"Organic": 1.0, "Paid Search": 1.0, "Paid Social": 0.7, "Email & Referral": 1.25}
TASTE = rng2.gamma(0.7, 1 / 0.7, len(customers)) * customers.acquisition_channel.map(CH_MULT).values
LEAVE = SIGN + (rng2.exponential(420, len(customers)) + 60).astype("timedelta64[D]")
ab_rows = []; orders = []; lines = []; oid = 500000
def day_pool(d):
    t = np.datetime64(d)
    idx = np.where(SIGN <= t)[0]
    w = np.where(SIGN[idx] > t - np.timedelta64(120, "D"), 2.2, 1.0) * TASTE[idx] * np.where(LEAVE[idx] > t, 1.0, 0.04)
    w /= w.sum()
    return idx, w

def pick_customer(pool):
    idx, w = pool
    return customers.iloc[int(rng.choice(idx, p=w))]

def discount_for(d, cust_id, ab_group):
    if date(2025, 10, 1) <= d <= date(2025, 12, 31): return 0.20, "SITEWIDE20"
    if ab_group == "Treatment": return 0.20, "TEST20"
    if date(2024, 11, 29) <= d <= date(2024, 12, 2) or date(2025, 11, 28) <= d <= date(2025, 12, 1): return 0.15, "BLACKFRI15"
    if rng.random() < 0.08: return 0.10, "WELCOME10"
    return 0.0, ""

def make_order(d, c, ab_group=None):
    global oid
    oid += 1
    mix = mix24 if d.year == 2024 else mix25
    disc, code = discount_for(d, c.customer_id, ab_group)
    n = int(rng.choice([1, 1, 1, 2, 2, 3]))
    hh, mm = int(rng.choice(range(24), p=HOURS)), int(rng.integers(0, 60))
    ts = datetime(d.year, d.month, d.day, hh, mm)
    orders.append(dict(order_id=f"HH{oid}", customer_id=c.customer_id, order_ts_local=ts, discount_pct=disc, promo_code=code))
    for _ in range(n):
        cat = str(rng.choice(list(mix), p=list(mix.values())))
        if cat == "Lighting" and d.year == 2025 and rng.random() < 0.40:
            p = by_cat[cat][by_cat[cat].sku == AURORA].iloc[0]          # 2025 bestseller
        else:
            p = by_cat[cat].iloc[int(rng.integers(len(by_cat[cat])))]
        q = int(rng.choice([1, 1, 1, 1, 2, 2, 3])) if cat in ("Textiles", "Kitchen") else int(rng.choice([1, 1, 1, 2]))
        lines.append(dict(order_id=f"HH{oid}", sku=p.sku, quantity=q, unit_price=p.list_price))

day = date(2024, 1, 1)
while day <= date(2025, 12, 31):
    if day.year == 2025 and day.month == 9:   # September 2025: the A/B test month, handled below
        day += timedelta(days=1); continue
    base = 21.0 if day.year == 2024 else 24.4
    if date(2025, 10, 1) <= day <= date(2025, 12, 31): base *= 1.06       # promo lifted volume only a little
    if day.weekday() >= 5: base *= 1.15
    pool = day_pool(day)
    for _ in range(rng.poisson(base * season[day.month])):
        make_order(day, pick_customer(pool))
    day += timedelta(days=1)

# A/B test: Sep 1-30 2025, active customers split 50/50; treatment sees 20% off
active = customers[customers.signup_date <= date(2025, 8, 31)].sample(6000, random_state=7).reset_index(drop=True)
active["grp"] = np.where(rng.random(len(active)) < 0.5, "Control", "Treatment")
for _, c in active.iterrows():
    ab_rows.append(dict(customer_id=c.customer_id, test_group=c.grp, assigned_date="2025-09-01"))
    p_buy = 0.105 if c.grp == "Control" else 0.117
    if rng.random() < p_buy:
        for _ in range(int(rng.choice([1, 1, 1, 2]))):
            make_order(date(2025, 9, int(rng.integers(1, 31))), c, c.grp)

orders = pd.DataFrame(orders); lines = pd.DataFrame(lines)
lines = lines.merge(products[["sku", "weight_kg"]], on="sku")
orders = orders.sort_values("order_ts_local").reset_index(drop=True)

# ---------------------------------------------------------------- shipping (free to customer, a cost to us)
w = lines.assign(w=lines.quantity * lines.weight_kg).groupby("order_id").w.sum()
ship = []
for o in orders.itertuples():
    kg = float(w[o.order_id]); d = o.order_ts_local.date()
    if d >= date(2025, 4, 1) and kg > 10:
        carrier, cost = "SwiftShip", 9.0 + 1.75 * kg
    else:
        carrier, cost = "ParcelPro", 6.0 + 0.85 * kg
    ship.append(dict(order_id=o.order_id, carrier=carrier, billed_weight_kg=round(kg, 1), ship_cost=round(cost * float(rng.uniform(0.97, 1.03)), 2)))
shipping = pd.DataFrame(ship)

# ---------------------------------------------------------------- returns
od = orders.set_index("order_id")
ret = []
for l in lines.itertuples():
    d = od.loc[l.order_id, "order_ts_local"].date()
    rate, reason = 0.05, None
    if l.sku == AURORA and date(2025, 5, 1) <= d <= date(2025, 10, 31): rate = 0.45
    if rng.random() < rate:
        if l.sku == AURORA and rate > 0.1 and rng.random() < 0.9: reason = "Defective - flickering"
        else: reason = str(rng.choice(["Changed mind", "Not as described", "Arrived damaged", "Wrong size"], p=[.45, .25, .2, .1]))
        ret.append(dict(order_id=l.order_id, sku=l.sku, quantity_returned=l.quantity,
                        return_date=d + timedelta(days=int(rng.integers(5, 30))), reason=reason))
returns = pd.DataFrame(ret)

# ---------------------------------------------------------------- marketing spend (monthly)
mk = []
for y in (2024, 2025):
    for m in range(1, 13):
        for ch, base in [("Paid Search", 21000), ("Paid Social", 14000 if y == 2024 else 17500), ("Email & Referral", 4000)]:
            mk.append(dict(month=f"{y}-{m:02d}", channel=ch, spend=round(base * season[m] * float(rng.uniform(.95, 1.05)), 0)))
marketing = pd.DataFrame(mk)

# ---------------------------------------------------------------- write the messy exports
cut = datetime(2025, 7, 1)
ol = orders.merge(lines.drop(columns="weight_kg"), on="order_id")
legacy = ol[ol.order_ts_local < datetime(2025, 7, 11)].copy()          # BUG: legacy export ran 10 days past cutover
legacy["order_ts_local"] = legacy.order_ts_local.dt.strftime("%m/%d/%Y %H:%M")
test = pd.DataFrame([dict(order_id=f"TEST{i}", customer_id="TEST", order_ts_local="03/15/2025 10:00", discount_pct=0.0, promo_code="",
                          sku="HH-KIT-001", quantity=1, unit_price=0.0) for i in range(1, 9)])
pd.concat([legacy, test]).to_csv(RAW / "orders_legacy.csv", index=False)

newp = ol[ol.order_ts_local >= cut].copy()
newp["order_ts_utc"] = (newp.order_ts_local.dt.tz_localize("America/New_York", ambiguous=False, nonexistent="shift_forward").dt.tz_convert("UTC")).dt.strftime("%Y-%m-%dT%H:%M:%SZ")
recs = []
for oid_, g in newp.groupby("order_id", sort=False):
    f = g.iloc[0]
    recs.append(dict(id=oid_, customer=f.customer_id, created_at=f.order_ts_utc, discount=f.discount_pct, promo=f.promo_code,
                     items=[dict(sku=(s.lower() if rng.random() < 0.03 else s), qty=int(q), price=float(p)) for s, q, p in zip(g.sku, g.quantity, g.unit_price)]))
json.dump(recs, open(RAW / "orders_new_platform.json", "w"), indent=1)

c2 = customers.copy()
mess = rng.random(len(c2))
c2.loc[mess < 0.04, "state"] = c2.loc[mess < 0.04, "state"].str.lower()
c2.loc[(mess >= 0.04) & (mess < 0.06), "state"] = " " + c2.loc[(mess >= 0.04) & (mess < 0.06), "state"] + " "
c2.to_csv(RAW / "customers.csv", index=False)
products.to_excel(RAW / "products.xlsx", index=False, sheet_name="catalog")
returns.to_csv(RAW / "returns.csv", index=False)
shipping.to_csv(RAW / "shipping_invoices.csv", index=False)
marketing.to_csv(RAW / "marketing_spend.csv", index=False)
pd.DataFrame(ab_rows).to_csv(RAW / "ab_test_assignments.csv", index=False)
print("orders", len(orders), "lines", len(lines), "customers", len(customers), "returns", len(returns))
