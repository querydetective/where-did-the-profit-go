-- The headline: revenue up, profit down?
SELECT year,
       SUM(orders)                         AS orders,
       ROUND(SUM(gross_sales))             AS gross_sales,
       ROUND(SUM(discounts))               AS discounts,
       ROUND(SUM(net_sales))               AS net_sales,
       ROUND(SUM(refunds))                 AS refunds,
       ROUND(SUM(cogs))                    AS cogs,
       ROUND(SUM(shipping))                AS shipping,
       ROUND(SUM(contribution_profit))     AS contribution_profit,
       ROUND(100.0 * SUM(contribution_profit) / SUM(net_sales), 1) AS margin_pct
FROM mart_monthly_pnl
GROUP BY year;
