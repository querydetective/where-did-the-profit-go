-- Where did the discounts come from?
SELECT CAST(SUBSTR(order_date, 1, 4) AS INT) AS year,
       CASE WHEN promo_code = '' THEN '(none)' ELSE promo_code END AS promo_code,
       COUNT(DISTINCT order_id)  AS orders,
       ROUND(SUM(discount))      AS discount_given
FROM fact_order_line
GROUP BY 1, 2
HAVING SUM(discount) > 0
ORDER BY year, discount_given DESC;
