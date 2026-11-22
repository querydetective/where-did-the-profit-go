# Decision log

Choices a reviewer might question, and why they were made.

| # | Decision | Alternatives | Why |
|---|---|---|---|
| 1 | SQLite as the warehouse | Postgres, DuckDB, Snowflake | Ships with Python, so anyone can run the project in one command; the SQL (CTEs, window functions) carries over to any warehouse. |
| 2 | Deduplicate migration overlap at the order level, preferring the new platform | Drop rows with identical order, SKU, quantity and price | The column match deleted 141 real lines. An order exported by both systems is the true duplicate; the new platform is the system of record after cut-over. |
| 3 | Convert UTC to Eastern before any date logic | Leave UTC | Late-evening orders on Dec 31 otherwise land in the next year, and monthly totals shift. |
| 4 | Contribution profit excludes marketing | Include marketing | Marketing changed little (+6%) and is decided separately; keeping it out makes the operational drivers visible. It is still reported. |
| 5 | Defective returns recover no product cost | Recover cost on every return | A flickering lamp cannot be resold. Treating it as resellable would hide the cost of the bad batch. |
| 6 | Profit bridge at 2024 rates per dollar of gross sales, by category | Simple year-over-year differences | Separates volume, mix, discount, returns, shipping and cost effects, and the pieces add up exactly to the total change (asserted in code). |
| 7 | Judge the A/B test on profit per customer, not only conversion | Conversion only | A discount can "win" on conversion and still lose money. The test answers the business question, with a 95% confidence interval. |
| 8 | Tests run before analysis, and the pipeline stops on failure | Run tests separately | A report built on broken data is worse than no report. |
| 9 | Synthetic data with a fixed seed | A public dataset | Lets the project include realistic problems (two systems, a migration, a defect) and stay fully reproducible and shareable. |
