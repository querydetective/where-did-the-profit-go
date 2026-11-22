# Interview kit: "Where Did the Profit Go?"

## The 60-second pitch
> An online home-goods company grew sales almost 19% but lost 18% of its profit, and nobody could say why. I took seven messy exports from two order systems, cleaned them into a SQLite warehouse with fact and dimension tables, and wrote eleven automated data-quality tests that run before any analysis. Then I built a profit bridge that splits the $169K drop into volume, mix, discounts, shipping and returns, and the pieces add up exactly. Three things stood out: a sitewide 20% discount that a randomized test showed didn't significantly raise conversion but cost about $6.68 of profit per customer; a shipping carrier change that doubled heavy-parcel costs; and one lamp whose defect rate jumped to almost a quarter of units sold. I also found the existing dashboard overstated growth because orders were exported twice during a migration. Everything runs from one command and ends in an Excel workbook, a dashboard and a short executive memo with five recommendations.

## STAR answer: "Tell me about a time your analysis changed a decision."
- **Situation:** Sales were up 18.8% but contribution profit was down 17.8%. Leadership wanted to know why before planning next year's promotions.
- **Task:** Explain the profit drop with numbers that add up, and say what to do.
- **Action:** Combined two order systems (time zones, SKU codes, test orders, migration duplicates), built a tested warehouse, decomposed the change into six drivers, and re-analyzed the September A/B test on profit instead of conversion.
- **Result:** Discounts explained $232K of lost profit, and the test showed the discount didn't significantly lift conversion (p = 0.34) while lowering profit per customer (95% CI -$9.65 to -$3.71). Recommendations: stop the sitewide discount, re-bid heavy shipping ($85K), claim the defective lamp batch ($51K), and fix the dashboard, which overstated growth by 3 points.

## Questions to expect, with short answers
- **Why SQLite?** So anyone can reproduce it with one command. The SQL is standard and moves to Postgres or Snowflake unchanged.
- **How do you know the numbers are right?** Eleven tests: unique keys, no orphans, row counts reconcile from staging to facts, mart totals equal fact totals. The profit bridge asserts that its pieces sum to the total change.
- **What was the hardest bug?** A deduplication rule that matched on order, SKU, quantity and price deleted 141 real lines. I switched to an order-level rule based on how the migration actually worked.
- **Isn't the conversion lift real, just small?** Maybe, but at this sample size we can't tell it from noise (p = 0.34), and even if it were real, the profit loss per customer is clearly negative. The decision doesn't depend on the conversion result.
- **What would you do next?** Customer lifetime value and segmentation: which customers the discount actually brought in, and whether they came back.
- **Limitations?** Synthetic data; contribution profit excludes overhead; the bridge uses 2024 rates as the baseline, so a different baseline order would shift the split slightly (not the total).

## Resume bullets (pick two or three)
- Built an end-to-end analytics pipeline (Python, SQL, SQLite) that cleans 7 raw exports from two order systems into a star-schema warehouse, guarded by 11 automated data-quality tests and run with one command.
- Explained a 17.8% profit decline despite 18.8% sales growth with a six-driver profit bridge that reconciles exactly, identifying $232K in discount losses, $85K in excess shipping and $51K in defect-driven returns.
- Re-analyzed an A/B test on profit per customer (Welch t-test, 95% CI) and showed a 20% discount reduced profit by $6.68 per customer with no significant conversion lift.
- Found a migration duplication issue that overstated reported growth by 3 points (about $75K of revenue).
- Delivered findings as an Excel workbook with native charts, a self-contained HTML dashboard and a short executive memo with five recommendations.

## LinkedIn post (short)
Sales up 19%. Profit down 18%. Where did it go?

I built an end-to-end analytics project to answer that: messy exports from two systems, a tested SQL warehouse, a profit bridge that adds up to the dollar, and an A/B test judged on profit instead of clicks.

The discount everyone loved? It didn't significantly change conversion, and it cost $6.68 of profit per customer.

Code, data, dashboard and memo are in the repo. Link in the comments.

## Act 2 and Act 3 additions

**Extra resume bullets**
- Designed and analyzed a 3-arm, 89,000-visitor website experiment: sized it in advance (Bonferroni, 80% power), caught a sample ratio mismatch caused by bots and duplicate assignments, and recommended a non-discount page change (+10.6% conversion, about +$107K a year) over a 10% discount (about -$301K a year).
- Built customer lifetime value and RFM segments validated on a time-based holdout; a gradient boosting model reached 49% of next-half-year profit when targeting the top 20% of customers, vs 40% for segments.

**Questions to expect**
- *Why didn't you stop the test when B was significant in February?* Peeking inflates false alarms and early weeks have novelty effects; B's lift faded from about 20% to 5.5% (p = 0.21) by the planned end.
- *What is a sample ratio mismatch?* Arms not the size randomization should give. Here: a crawler and visitors in two arms. Remove, re-check (p = 0.21), then read results.
- *How did you validate the segments?* Built on data to 30 Jun 2025, compared with July to December behavior: Champions 65% bought again, Hibernating 14%.
- *Why not use mean absolute error?* It rewarded predicting $0 for everyone. The decision is who to target, so measure profit captured in the top 20%.
