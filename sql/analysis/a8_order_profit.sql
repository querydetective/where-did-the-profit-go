-- Contribution profit for every order: the building block for customer value.
-- Sums to exactly the same total as mart_monthly_pnl (a test checks it).
WITH sales AS (
    SELECT customer_id, order_id, MIN(order_date) AS order_date,
           SUM(net_sales) AS net_sales, SUM(cogs) AS cogs
    FROM fact_order_line
    GROUP BY customer_id, order_id
), ret AS (
    SELECT order_id, SUM(refund) AS refunds, SUM(cogs_recovered) AS cogs_recovered
    FROM fact_return
    GROUP BY order_id
)
SELECT s.customer_id, s.order_id, s.order_date, s.net_sales,
       ROUND(s.net_sales - COALESCE(r.refunds, 0)
             - (s.cogs - COALESCE(r.cogs_recovered, 0))
             - sh.ship_cost, 2) AS profit
FROM sales s
LEFT JOIN ret r      ON r.order_id = s.order_id
JOIN fact_shipment sh ON sh.order_id = s.order_id;
