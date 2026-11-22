# Data dictionary

All money is US dollars. All dates are in store local time (America/New_York).

## Raw exports (`data/raw`)

| File | Grain | Known problems |
|---|---|---|
| orders_legacy.csv | one row per order line, legacy system (Jan 2024 to Jul 11 2025) | US date format, local time; ran 10 days past the cut-over, so some orders also appear in the new platform; 8 internal TEST orders |
| orders_new_platform.json | one object per order with nested items (from Jul 1 2025) | timestamps in UTC; some SKUs lower case |
| customers.csv | one row per customer | state codes in mixed case with spaces |
| products.xlsx (sheet `catalog`) | one row per SKU | none |
| returns.csv | one row per returned line | none |
| shipping_invoices.csv | one row per shipped order | none |
| marketing_spend.csv | one row per month and channel | none |
| ab_test_assignments.csv | one row per customer in the September 2025 test | none |

## Warehouse (`warehouse/harbor_hearth.db`)

### Dimensions
| Table | Key | Columns |
|---|---|---|
| dim_customer | customer_id | signup_date, state, acquisition_channel, cohort_month (month of first order) |
| dim_product | sku | product_name, category, list_price, unit_cost, weight_kg |
| dim_date | date | year, quarter, month, is_weekend (built with a recursive CTE) |

### Facts
| Table | Grain | Columns |
|---|---|---|
| fact_order_line | order line | order_id, customer_id, order_date, sku, quantity, gross_sales (qty x price), discount, net_sales, cogs (qty x unit cost), promo_code, source (legacy or new) |
| fact_shipment | order | order_id, order_date, carrier, billed_weight_kg, ship_cost |
| fact_return | returned line | order_id, sku, order_date, return_date, reason, quantity_returned, refund (quantity x net unit price), cogs_recovered (0 if defective, else the unit cost, because the item is resold), return_cost (refund - cogs_recovered) |

### Marts
| Table | Grain | Notes |
|---|---|---|
| mart_monthly_pnl | month | orders, gross_sales, discounts, net_sales, refunds, cogs (net of recovered), shipping, contribution_profit, marketing |
| mart_category_year | year x category | sales, discounts, refunds, cogs, product_margin_pct |

## Definitions
- **Net sales** = gross sales - discounts.
- **Contribution profit** = net sales - refunds - (product cost - cost recovered from resellable returns) - shipping. Marketing is reported beside it, not inside it, because spend decisions are reviewed separately.
- **Return rate** = units returned / units sold, by month of sale.
