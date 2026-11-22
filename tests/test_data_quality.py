"""Data-quality tests. Run with:  pytest -q
If any of these fail, the numbers in the report can't be trusted."""
import sqlite3, sys
from pathlib import Path
import pytest
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from config import WAREHOUSE

@pytest.fixture(scope="module")
def db():
    con = sqlite3.connect(WAREHOUSE); yield con; con.close()

def one(db, sql): return db.execute(sql).fetchone()[0]

def test_order_ids_are_unique(db):
    assert one(db, "SELECT COUNT(*) - COUNT(DISTINCT order_id) FROM stg_orders") == 0

def test_no_migration_duplicates_left(db):
    # the same order must not appear as two different header rows
    assert one(db, "SELECT COUNT(*) FROM (SELECT order_id FROM stg_orders GROUP BY order_id HAVING COUNT(*) > 1)") == 0

def test_no_test_orders(db):
    assert one(db, "SELECT COUNT(*) FROM stg_orders WHERE customer_id = 'TEST'") == 0

def test_every_line_has_a_known_product(db):
    assert one(db, "SELECT COUNT(*) FROM stg_order_lines l LEFT JOIN dim_product p ON p.sku = l.sku WHERE p.sku IS NULL") == 0

def test_every_order_has_a_known_customer(db):
    assert one(db, "SELECT COUNT(*) FROM stg_orders o LEFT JOIN dim_customer c ON c.customer_id = o.customer_id WHERE c.customer_id IS NULL") == 0

def test_fact_keeps_every_line(db):
    # joins must not drop or duplicate lines
    assert one(db, "SELECT COUNT(*) FROM fact_order_line") == one(db, "SELECT COUNT(*) FROM stg_order_lines")

def test_returns_are_not_double_counted(db):
    assert one(db, "SELECT COUNT(*) FROM fact_return") == one(db, "SELECT COUNT(*) FROM stg_returns")

def test_every_order_has_one_shipment(db):
    assert one(db, "SELECT COUNT(*) FROM fact_shipment") == one(db, "SELECT COUNT(*) FROM stg_orders")

def test_no_negative_or_zero_prices(db):
    assert one(db, "SELECT COUNT(*) FROM fact_order_line WHERE gross_sales <= 0 OR quantity <= 0") == 0

def test_states_are_clean(db):
    assert one(db, "SELECT COUNT(*) FROM dim_customer WHERE state <> UPPER(TRIM(state)) OR LENGTH(state) <> 2") == 0

def test_mart_matches_fact_totals(db):
    # the monthly P&L must add up to the line-level facts, to the cent
    mart = one(db, "SELECT ROUND(SUM(net_sales), 2) FROM mart_monthly_pnl")
    fact = one(db, "SELECT ROUND(SUM(net_sales), 2) FROM fact_order_line")
    assert abs(mart - fact) < 0.01
