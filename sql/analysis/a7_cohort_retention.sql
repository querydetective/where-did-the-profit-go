-- Cohort retention: of customers whose FIRST order was in a quarter, what % ordered again in later quarters?
WITH firsts AS (
    SELECT customer_id, MIN(order_date) AS first_date FROM fact_order_line GROUP BY customer_id
), activity AS (
    SELECT DISTINCT f.customer_id,
           STRFTIME('%Y', fi.first_date) || '-Q' || ((CAST(STRFTIME('%m', fi.first_date) AS INT) + 2) / 3) AS cohort,
           (CAST(STRFTIME('%Y', f.order_date) AS INT) * 4 + (CAST(STRFTIME('%m', f.order_date) AS INT) - 1) / 3)
         - (CAST(STRFTIME('%Y', fi.first_date) AS INT) * 4 + (CAST(STRFTIME('%m', fi.first_date) AS INT) - 1) / 3) AS q_after
    FROM fact_order_line f JOIN firsts fi ON fi.customer_id = f.customer_id
)
SELECT cohort, q_after, COUNT(*) AS customers,
       ROUND(100.0 * COUNT(*) / FIRST_VALUE(COUNT(*)) OVER (PARTITION BY cohort ORDER BY q_after), 1) AS pct_of_cohort
FROM activity
GROUP BY cohort, q_after
ORDER BY cohort, q_after;
