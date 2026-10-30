SELECT
    s.region,
    COUNT(DISTINCT f.store_id) AS store_count,
    ROUND(SUM(f.net_sales), 2) AS net_sales,
    ROUND(SUM(f.net_sales - f.cogs), 2) AS gross_profit,
    ROUND(100.0 * SUM(f.net_sales - f.cogs) / NULLIF(SUM(f.net_sales), 0), 2) AS gp_margin_pct,
    ROUND(SUM(f.net_sales - f.cogs - f.labour_cost - f.occupancy_cost - f.other_store_cost), 2) AS store_contribution
FROM fact_store_month f
JOIN dim_store s ON f.store_id = s.store_id
GROUP BY s.region
ORDER BY net_sales DESC;
