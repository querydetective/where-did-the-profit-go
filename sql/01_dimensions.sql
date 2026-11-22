-- Dimension tables: who, what, when
DROP TABLE IF EXISTS dim_customer;
CREATE TABLE dim_customer AS
SELECT customer_id,
       DATE(signup_date)                  AS signup_date,
       state,
       acquisition_channel,
       SUBSTR(signup_date, 1, 7)          AS cohort_month
FROM stg_customers;

DROP TABLE IF EXISTS dim_product;
CREATE TABLE dim_product AS
SELECT sku, product_name, category, list_price, unit_cost, weight_kg
FROM stg_products;

DROP TABLE IF EXISTS dim_date;
CREATE TABLE dim_date AS
WITH RECURSIVE d(dt) AS (SELECT DATE('2024-01-01') UNION ALL SELECT DATE(dt, '+1 day') FROM d WHERE dt < '2025-12-31')
SELECT dt                                            AS date,
       CAST(STRFTIME('%Y', dt) AS INT)               AS year,
       'Q' || ((CAST(STRFTIME('%m', dt) AS INT) + 2) / 3) AS quarter,
       STRFTIME('%Y-%m', dt)                         AS month,
       CASE WHEN STRFTIME('%w', dt) IN ('0', '6') THEN 1 ELSE 0 END AS is_weekend
FROM d;
