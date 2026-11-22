from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
RAW, PROCESSED = ROOT / "data" / "raw", ROOT / "data" / "processed"
WAREHOUSE = ROOT / "warehouse" / "harbor_hearth.db"
SQL, REPORTS = ROOT / "sql", ROOT / "reports"
LOCAL_TZ = "America/New_York"
for p in (PROCESSED, WAREHOUSE.parent, REPORTS, REPORTS / "charts"):
    p.mkdir(parents=True, exist_ok=True)
