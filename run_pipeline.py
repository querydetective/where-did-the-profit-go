"""One command, whole project:  python run_pipeline.py
raw data -> clean -> warehouse -> tests -> analysis -> charts -> reports.
Stops at the first failure, so a red test never reaches a report."""
import subprocess, sys, time
from pathlib import Path

ROOT = Path(__file__).parent
STEPS = [
    ("Generate raw data",       [sys.executable, "src/generate_data.py"]),
    ("Generate experiment",     [sys.executable, "src/generate_experiment.py"]),
    ("Clean and combine",       [sys.executable, "src/clean.py"]),
    ("Load the warehouse",      [sys.executable, "src/load_warehouse.py"]),
    ("Data-quality tests",      [sys.executable, "-m", "pytest", "-q", "tests/test_data_quality.py"]),
    ("Investigate",             [sys.executable, "src/analysis.py"]),
    ("Analyze the experiment",  [sys.executable, "src/experiment.py"]),
    ("Value the customers",     [sys.executable, "src/customers.py"]),
    ("Experiment & customer tests", [sys.executable, "-m", "pytest", "-q", "tests/test_acts_2_3.py"]),
    ("Draw charts",             [sys.executable, "src/charts.py"]),
    ("Draw Act 2 & 3 charts",   [sys.executable, "src/charts_more.py"]),
    ("Write reports",           [sys.executable, "src/report.py"]),
]

def main():
    t0 = time.time()
    for i, (name, cmd) in enumerate(STEPS, 1):
        print(f"\n[{i}/{len(STEPS)}] {name}", flush=True)
        if subprocess.run(cmd, cwd=ROOT).returncode != 0:
            sys.exit(f"\nStopped: '{name}' failed. Nothing after it was run.")
    print(f"\nDone in {time.time() - t0:.0f}s. Open reports/dashboard.html")

if __name__ == "__main__":
    main()
