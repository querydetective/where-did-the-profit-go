"""Checks for Act 2 (the experiment) and Act 3 (customer value). Run after experiment.py and customers.py."""
import json, sqlite3, sys
from pathlib import Path
import pandas as pd
import pytest
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from config import WAREHOUSE, SQL, REPORTS

@pytest.fixture(scope="module")
def db():
    con = sqlite3.connect(WAREHOUSE); yield con; con.close()

def one(db, sql): return db.execute(sql).fetchone()[0]

def test_each_visitor_in_exactly_one_arm(db):
    assert one(db, "SELECT COUNT(*) FROM (SELECT visitor_id FROM stg_experiment GROUP BY visitor_id HAVING COUNT(DISTINCT arm) > 1)") == 0

def test_no_bots_left(db):
    assert one(db, "SELECT COUNT(*) FROM stg_experiment WHERE pageviews >= 60 AND seconds_on_site = 0") == 0

def test_split_is_even_after_cleaning():
    assert json.load(open(REPORTS / "experiment.json"))["srm"]["clean_p"] > 0.01

def test_order_profit_matches_pnl(db):
    # customer value must be built from exactly the same profit as the P&L
    orders = pd.read_sql((SQL / "analysis" / "a8_order_profit.sql").read_text(), db)
    assert abs(orders.profit.sum() - one(db, "SELECT SUM(contribution_profit) FROM mart_monthly_pnl")) < 1

def test_every_buyer_has_one_segment(db):
    assert one(db, "SELECT COUNT(*) FROM mart_customer_value") == one(db, "SELECT COUNT(DISTINCT customer_id) FROM fact_order_line")
    assert one(db, "SELECT COUNT(*) FROM mart_customer_value WHERE segment IS NULL") == 0
