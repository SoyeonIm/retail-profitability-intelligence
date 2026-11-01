
-- Step 15: Regional Reporting Layer
-- Grain: One row per region per month
-- Do not join category-level records directly into this view.

SELECT
    -- Dimensions
    r.region,
    r.month,
    r.store_count,

    -- Financial metrics
    r.net_sales_cents,
    r.cogs_cents,
    r.gross_profit_cents,
    r.sale_discount_cents,

    -- Transaction metrics
    r.sale_lines,
    r.return_lines,

    -- Regional profitability
    r.regional_gp_margin_pct,
    r.nz_gp_margin_pct,
    r.margin_variance_pp,
    r.sales_contribution_pct,
    r.gp_contribution_pct,
    r.regional_gp_margin_rank,

    -- Trends
    t.mom_margin_change_pp,
    t.yoy_margin_change_pp,
    t.rolling_3m_sales_cents,
    t.rolling_3m_gp_cents,
    t.rolling_3m_month_count,
    t.rolling_3m_gp_margin_pct,

    -- Benchmark monitoring
    t.below_nz_benchmark,
    t.below_benchmark_streak

FROM regional_profitability r

INNER JOIN profitability_trends t
    ON r.region = t.region
   AND r.month = t.month

ORDER BY r.month, r.region;
