-- Which products cost us the most in returns, and how fast are they coming back?
WITH sold AS (
    SELECT CAST(SUBSTR(order_date, 1, 4) AS INT) AS year, sku, SUM(quantity) AS units_sold
    FROM fact_order_line GROUP BY 1, 2
), ret AS (
    SELECT CAST(SUBSTR(order_date, 1, 4) AS INT) AS year, sku, SUM(quantity_returned) AS units_returned,
           SUM(return_cost) AS return_cost,
           SUM(CASE WHEN reason LIKE 'Defective%' THEN quantity_returned ELSE 0 END) AS defective_units
    FROM fact_return GROUP BY 1, 2
)
SELECT r.year, p.product_name, p.category, s.units_sold, r.units_returned,
       ROUND(100.0 * r.units_returned / s.units_sold, 1) AS return_rate_pct,
       r.defective_units, ROUND(r.return_cost) AS return_cost,
       RANK() OVER (PARTITION BY r.year ORDER BY r.return_cost DESC) AS cost_rank
FROM ret r
JOIN sold s        ON s.year = r.year AND s.sku = r.sku
JOIN dim_product p ON p.sku = r.sku
ORDER BY r.year, cost_rank
;
