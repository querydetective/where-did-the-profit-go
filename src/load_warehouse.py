"""Step 2: load the clean files into a SQLite warehouse and build the star schema."""
import sqlite3
import pandas as pd
from config import PROCESSED, WAREHOUSE, SQL

STAGING = ["orders", "order_lines", "customers", "products", "returns", "shipping", "marketing", "ab_test"]

def main():
    print("Loading warehouse:", WAREHOUSE.name)
    if WAREHOUSE.exists(): WAREHOUSE.unlink()
    con = sqlite3.connect(WAREHOUSE)
    for t in STAGING:
        df = pd.read_csv(PROCESSED / f"{t}.csv", dtype={"promo_code": str})
        df.to_sql(f"stg_{t}", con, index=False)
        print(f"  stg_{t:<12} {len(df):>7} rows")
    for f in sorted(SQL.glob("0*.sql")):
        con.executescript(f.read_text()); print("  ran", f.name)
    for t in ["dim_customer", "dim_product", "dim_date", "fact_order_line", "fact_shipment", "fact_return", "mart_monthly_pnl", "mart_category_year"]:
        print(f"  {t:<18} {con.execute(f'SELECT COUNT(*) FROM {t}').fetchone()[0]:>7} rows")
    con.commit(); con.close()

if __name__ == "__main__":
    main()
