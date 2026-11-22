-- Business-ready marts. Contribution profit = what's left after product cost,
-- discounts, returns and shipping (before marketing and overhead).
DROP TABLE IF EXISTS mart_monthly_pnl;
CREATE TABLE mart_monthly_pnl AS
WITH sales AS (
    SELECT SUBSTR(order_date, 1, 7) AS month, SUM(gross_sales) AS gross_sales, SUM(discount) AS discounts,
           SUM(net_sales) AS net_sales, SUM(cogs) AS cogs, COUNT(DISTINCT order_id) AS orders
    FROM fact_order_line GROUP BY 1
), rets AS (
    SELECT SUBSTR(order_date, 1, 7) AS month, SUM(refund) AS refunds, SUM(cogs_recovered) AS cogs_recovered, SUM(return_cost) AS return_cost
    FROM fact_return GROUP BY 1
), ship AS (
    SELECT SUBSTR(order_date, 1, 7) AS month, SUM(ship_cost) AS shipping FROM fact_shipment GROUP BY 1
), mkt AS (
    SELECT month, SUM(spend) AS marketing FROM stg_marketing GROUP BY 1
)
SELECT s.month, CAST(SUBSTR(s.month, 1, 4) AS INT) AS year, s.orders,
       ROUND(s.gross_sales, 2) AS gross_sales, ROUND(s.discounts, 2) AS discounts, ROUND(s.net_sales, 2) AS net_sales,
       ROUND(COALESCE(r.refunds, 0), 2) AS refunds,
       ROUND(s.cogs - COALESCE(r.cogs_recovered, 0), 2) AS cogs,
       ROUND(sh.shipping, 2) AS shipping,
       ROUND(s.net_sales - COALESCE(r.refunds, 0) - (s.cogs - COALESCE(r.cogs_recovered, 0)) - sh.shipping, 2) AS contribution_profit,
       ROUND(m.marketing, 2) AS marketing
FROM sales s
LEFT JOIN rets r  ON r.month = s.month
LEFT JOIN ship sh ON sh.month = s.month
LEFT JOIN mkt m   ON m.month = s.month
ORDER BY s.month;

DROP TABLE IF EXISTS mart_category_year;
CREATE TABLE mart_category_year AS
WITH s AS (
    SELECT CAST(SUBSTR(f.order_date, 1, 4) AS INT) AS year, p.category,
           SUM(f.gross_sales) AS gross_sales, SUM(f.discount) AS discounts, SUM(f.net_sales) AS net_sales, SUM(f.cogs) AS cogs
    FROM fact_order_line f JOIN dim_product p ON p.sku = f.sku GROUP BY 1, 2
), r AS (
    SELECT CAST(SUBSTR(r.order_date, 1, 4) AS INT) AS year, p.category, SUM(r.refund) AS refunds, SUM(r.cogs_recovered) AS cogs_recovered
    FROM fact_return r JOIN dim_product p ON p.sku = r.sku GROUP BY 1, 2
)
SELECT s.year, s.category, ROUND(s.gross_sales, 2) AS gross_sales, ROUND(s.discounts, 2) AS discounts, ROUND(s.net_sales, 2) AS net_sales,
       ROUND(COALESCE(r.refunds, 0), 2) AS refunds, ROUND(s.cogs - COALESCE(r.cogs_recovered, 0), 2) AS cogs,
       ROUND(100.0 * (s.gross_sales - s.cogs) / s.gross_sales, 1) AS product_margin_pct
FROM s LEFT JOIN r ON r.year = s.year AND r.category = s.category
ORDER BY s.year, s.net_sales DESC;
