-- The September 2025 A/B test: did 20% off pay for itself?
WITH buyers AS (
    SELECT f.customer_id,
           COUNT(DISTINCT f.order_id)  AS orders,
           SUM(f.net_sales)            AS net_sales,
           SUM(f.net_sales - f.cogs)   AS product_profit
    FROM fact_order_line f
    WHERE f.order_date BETWEEN '2025-09-01' AND '2025-09-30'
    GROUP BY f.customer_id
)
SELECT a.test_group,
       COUNT(*)                                          AS customers,
       COUNT(b.customer_id)                              AS buyers,
       ROUND(100.0 * COUNT(b.customer_id) / COUNT(*), 2) AS conversion_pct,
       ROUND(SUM(COALESCE(b.net_sales, 0)))              AS net_sales,
       ROUND(SUM(COALESCE(b.net_sales, 0)) / COUNT(*), 2)      AS sales_per_customer,
       ROUND(SUM(COALESCE(b.product_profit, 0)) / COUNT(*), 2) AS product_profit_per_customer
FROM stg_ab_test a
LEFT JOIN buyers b ON b.customer_id = a.customer_id
GROUP BY a.test_group;
