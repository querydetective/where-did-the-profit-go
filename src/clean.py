"""Step 1: extract the raw exports, clean them, and write tidy CSVs.

Every fix is logged, so the cleaning is auditable (data/processed/cleaning_log.csv).
"""
import json
import pandas as pd
from config import RAW, PROCESSED, LOCAL_TZ

log = []
def note(step, rows, detail):
    log.append(dict(step=step, rows_affected=int(rows), detail=detail))
    print(f"  {step:<34} {rows:>6}  {detail}")

def clean_orders():
    # Legacy system: local Eastern time, US date format
    legacy = pd.read_csv(RAW / "orders_legacy.csv", dtype={"promo_code": str})
    legacy["order_ts"] = pd.to_datetime(legacy.order_ts_local, format="%m/%d/%Y %H:%M")
    legacy["source"] = "legacy"
    # New platform (from July 2025): nested JSON, timestamps in UTC
    recs = json.load(open(RAW / "orders_new_platform.json"))
    new = pd.json_normalize(recs, record_path="items", meta=["id", "customer", "created_at", "discount", "promo"])
    new = new.rename(columns={"id": "order_id", "customer": "customer_id", "discount": "discount_pct", "promo": "promo_code", "qty": "quantity", "price": "unit_price"})
    new["order_ts"] = pd.to_datetime(new.created_at, utc=True).dt.tz_convert(LOCAL_TZ).dt.tz_localize(None)
    new["source"] = "new_platform"
    note("convert UTC to Eastern time", len(new), "new platform timestamps were UTC")
    cols = ["order_id", "customer_id", "order_ts", "discount_pct", "promo_code", "sku", "quantity", "unit_price", "source"]
    lines = pd.concat([legacy[cols], new[cols]], ignore_index=True)
    note("combine both systems", len(lines), f"{len(legacy)} legacy + {len(new)} new-platform lines")

    bad_sku = lines.sku != lines.sku.str.upper().str.strip()
    lines["sku"] = lines.sku.str.upper().str.strip()
    note("standardize SKU case", bad_sku.sum(), "e.g. hh-kit-004 -> HH-KIT-004")

    test = lines.customer_id.eq("TEST")
    lines = lines[~test]
    note("drop test orders", test.sum(), "customer_id = TEST, price 0")

    # An order that appears in BOTH systems is one order. Keep the new-platform copy.
    # (Matching on order+sku+qty+price would wrongly delete real repeat lines inside one order.)
    in_new = set(lines.loc[lines.source == "new_platform", "order_id"])
    dup = (lines.source == "legacy") & lines.order_id.isin(in_new)
    note("drop migration duplicates", dup.sum(), f"{lines[dup].order_id.nunique()} orders exported by BOTH systems")
    lines = lines[~dup].copy()
    lines["promo_code"] = lines.promo_code.fillna("")
    lines["order_date"] = lines.order_ts.dt.date
    return lines

def main():
    print("Cleaning raw data")
    lines = clean_orders()
    orders = lines.groupby("order_id", as_index=False).agg(customer_id=("customer_id", "first"), order_ts=("order_ts", "first"),
                                                           order_date=("order_date", "first"), discount_pct=("discount_pct", "first"),
                                                           promo_code=("promo_code", "first"), source=("source", "first"))
    order_lines = lines[["order_id", "sku", "quantity", "unit_price"]]

    cust = pd.read_csv(RAW / "customers.csv")
    messy = cust.state != cust.state.str.strip().str.upper()
    cust["state"] = cust.state.str.strip().str.upper()
    note("standardize customer state", messy.sum(), "' nj ' -> 'NJ'")

    products = pd.read_excel(RAW / "products.xlsx", sheet_name="catalog")
    returns = pd.read_csv(RAW / "returns.csv")
    shipping = pd.read_csv(RAW / "shipping_invoices.csv")
    marketing = pd.read_csv(RAW / "marketing_spend.csv")
    ab = pd.read_csv(RAW / "ab_test_assignments.csv")

    orphan = ~shipping.order_id.isin(orders.order_id)
    note("check shipping invoices match orders", orphan.sum(), "invoices with no matching order")

    for name, df in dict(orders=orders, order_lines=order_lines, customers=cust, products=products, returns=returns,
                         shipping=shipping, marketing=marketing, ab_test=ab).items():
        df.to_csv(PROCESSED / f"{name}.csv", index=False)
    pd.DataFrame(log).to_csv(PROCESSED / "cleaning_log.csv", index=False)
    print(f"  wrote {len(orders)} orders, {len(order_lines)} order lines")

if __name__ == "__main__":
    main()
