-- Run against the database built in Step 1.
-- Replace table names only if your build_database.py uses different names.
-- Audit 1: store-month uniqueness and null keys.
SELECT store_id, month, COUNT(*) AS row_count
FROM fact_store_month
GROUP BY store_id, month
HAVING COUNT(*) > 1;

-- Audit 2: potential pre-opening financial periods.
SELECT COUNT(*) AS pre_opening_rows
FROM fact_store_month f
JOIN dim_store s USING (store_id)
WHERE CAST(f.month AS DATE) < CAST(s.open_date AS DATE);

-- Audit 3: company-wide weighted GP margin.
SELECT ROUND(100 * SUM(net_sales - cogs) / NULLIF(SUM(net_sales),0), 2) AS weighted_gp_margin_pct
FROM fact_store_month;

-- Audit 4: store-level range, avoiding region-average-only analysis.
SELECT f.store_id, s.region,
       ROUND(SUM(f.net_sales),2) AS net_sales,
       ROUND(100 * SUM(f.net_sales - f.cogs) / NULLIF(SUM(f.net_sales),0),2) AS gp_margin_pct
FROM fact_store_month f
JOIN dim_store s USING (store_id)
GROUP BY f.store_id, s.region
ORDER BY gp_margin_pct ASC;
