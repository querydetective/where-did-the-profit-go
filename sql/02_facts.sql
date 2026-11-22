-- Fact tables: one row per order line, per order (shipping), per return
DROP TABLE IF EXISTS fact_order_line;
CREATE TABLE fact_order_line AS
SELECT ol.order_id,
       o.customer_id,
       DATE(o.order_date)                                   AS order_date,
       ol.sku,
       ol.quantity,
       ROUND(ol.quantity * ol.unit_price, 2)                AS gross_sales,
       ROUND(ol.quantity * ol.unit_price * o.discount_pct, 2) AS discount,
       ROUND(ol.quantity * ol.unit_price * (1 - o.discount_pct), 2) AS net_sales,
       ROUND(ol.quantity * p.unit_cost, 2)                  AS cogs,
       o.promo_code,
       o.source
FROM stg_order_lines ol
JOIN stg_orders  o ON o.order_id = ol.order_id
JOIN dim_product p ON p.sku = ol.sku;

DROP TABLE IF EXISTS fact_shipment;
CREATE TABLE fact_shipment AS
SELECT s.order_id, DATE(o.order_date) AS order_date, s.carrier, s.billed_weight_kg, s.ship_cost
FROM stg_shipping s
JOIN stg_orders o ON o.order_id = s.order_id;

-- A return refunds what the customer paid. Normal returns go back on the shelf
-- (we recover the product cost). Defective items are written off (we don't).
DROP TABLE IF EXISTS fact_return;
CREATE TABLE fact_return AS
WITH unit AS (   -- one row per order + product, so a return can't match two lines
    SELECT order_id, sku, MIN(order_date) AS order_date,
           SUM(net_sales) / SUM(quantity) AS unit_net, SUM(cogs) / SUM(quantity) AS unit_cogs
    FROM fact_order_line GROUP BY order_id, sku
)
SELECT r.order_id, r.sku, u.order_date, DATE(r.return_date) AS return_date, r.reason, r.quantity_returned,
       ROUND(r.quantity_returned * u.unit_net, 2) AS refund,
       ROUND(CASE WHEN r.reason LIKE 'Defective%' THEN 0 ELSE r.quantity_returned * u.unit_cogs END, 2) AS cogs_recovered,
       ROUND(r.quantity_returned * u.unit_net - CASE WHEN r.reason LIKE 'Defective%' THEN 0 ELSE r.quantity_returned * u.unit_cogs END, 2) AS return_cost
FROM stg_returns r
JOIN unit u ON u.order_id = r.order_id AND u.sku = r.sku;
