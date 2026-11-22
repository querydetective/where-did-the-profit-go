-- Shipping cost per order, by carrier and order weight
SELECT CAST(SUBSTR(order_date, 1, 4) AS INT) AS year,
       carrier,
       CASE WHEN billed_weight_kg > 10 THEN 'Heavy (>10 kg)' ELSE 'Light' END AS weight_band,
       COUNT(*)                               AS orders,
       ROUND(AVG(ship_cost), 2)               AS avg_cost_per_order,
       ROUND(SUM(ship_cost))                  AS total_cost
FROM fact_shipment
GROUP BY 1, 2, 3
ORDER BY year, carrier, weight_band;
