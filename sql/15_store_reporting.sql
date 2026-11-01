
-- Step 15: Store Reporting Layer
-- Grain: One row per store per month
-- Financial amounts are stored in integer NZD cents.
-- Benchmark shortfalls are hypothetical, not realised losses.

SELECT
    -- Dimensions
    s.store_id,
    s.region,
    s.month,
    s.floor_area_sqm,
    s.open_date,

    -- Financial metrics
    s.net_sales_cents,
    s.cogs_cents,
    s.gross_profit_cents,
    s.sale_discount_cents,

    -- Transaction metrics
    s.transaction_lines,
    s.sale_lines,
    s.return_lines,
    s.return_lines_per_100_sale_lines,

    -- Store performance
    s.gp_margin_pct,
    s.benchmark_gp_margin_pct,
    s.margin_variance_pp,
    s.sales_share_pct,
    s.gp_contribution_pct,

    -- National benchmark
    p.nz_gp_margin_pct,
    p.store_vs_nz_gap_pp,
    p.gp_shortfall_vs_nz_nzd,

    -- Regional diagnostic metrics
    d.region_gp_margin_pct,
    d.margin_gap_pp AS store_vs_region_gap_pp,
    d.gp_gap_impact_pp AS regional_gp_gap_impact_pp,
    d.gp_shortfall_nzd AS gp_shortfall_vs_region_nzd,

    -- Investigation metrics
    p.store_below_benchmark_streak,
    p.region_below_benchmark_streak,
    p.region_mom_change_pp,
    p.contribution_to_region_gap_pp,
    p.national_investigation_rank,
    p.investigation_priority,

    -- Regional category context, not store-level causes
    p.top_negative_category AS regional_negative_category,
    p.category_effect_pp AS regional_category_effect_pp,

    -- Store rankings
    s.sales_rank,
    s.gp_rank,
    s.gp_margin_rank

FROM store_performance s

INNER JOIN investigation_priorities p
    ON s.store_id = p.store_id
   AND s.region = p.region
   AND s.month = p.month

INNER JOIN store_profitability_diagnostics d
    ON s.store_id = d.store_id
   AND s.region = d.region
   AND s.month = d.month

ORDER BY s.month, s.store_id;
