-- Sales mix and margin by category
SELECT year, category, ROUND(net_sales) AS net_sales,
       ROUND(100.0 * net_sales / SUM(net_sales) OVER (PARTITION BY year), 1) AS share_pct,
       product_margin_pct
FROM mart_category_year
ORDER BY year, net_sales DESC;
