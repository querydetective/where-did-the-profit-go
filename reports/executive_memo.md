# Memo: where did the profit go?

**To:** Leadership team, Harbor & Hearth
**From:** Data analytics
**Re:** 2025 profit decline

## Bottom line
Net sales grew 18.8% in 2025, but contribution profit fell 17.8%, from $946K to $778K. Growth was real, but three business decisions and one supplier problem gave more than all of it back.

## What moved profit (2024 to 2025)
| Driver | Effect on contribution profit |
|---|---|
| More volume | +$267K |
| Discounts | -$232K |
| Sales mix | -$97K |
| Shipping | -$76K |
| Returns | -$32K |
| Product cost | +$2K |
| **Total change** | **-$169K** |

## Recommendations
1. **Stop the sitewide 20% discount.** Discounts cost $232K of profit. The September test showed 20% off moved conversion by only +0.77 points (p = 0.335, not significant) while cutting product profit by $6.68 per customer (95% CI -9.65 to -3.71).
2. **Re-bid heavy-parcel shipping.** Since April 2025 heavy orders go to SwiftShip at about twice the old rate. Shipping them at the ParcelPro heavy rate would have saved $85K in 2025.
3. **Claim the Aurora lamp defect from the supplier.** Aurora Standing Lamp returns jumped from 2.5% to 23.6%; 246 units came back 'Defective - flickering' (May to Oct 2025 batch), costing $51K. Recover the cost and add an incoming quality check.
4. **Price Smart Home for margin, not just volume.** Smart Home earns about 20% product margin and grew to about a quarter of sales; the mix shift cost $97K. Review pricing, bundles and ad spend for the category.
5. **Fix the dashboard before the next board meeting.** The current dashboard reads the raw exports and shows 21.8% growth instead of 18.8%: orders exported by both systems during the migration add about $75K of revenue that never happened.

## How we know
Seven raw exports from two order systems were cleaned (time zones, SKU case, test orders, migration duplicates), loaded into a SQLite warehouse with fact and dimension tables, and checked by 11 automated data-quality tests. Every figure above comes from that warehouse and is reproduced by one command: `python run_pipeline.py`.
