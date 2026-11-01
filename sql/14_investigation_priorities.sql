
-- Step 14: Profitability Investigation Priorities
-- Grain: One row per store per month
-- Regional category drivers provide context, not store-level causes.
-- Priority labels are investigation heuristics, not causal findings.

WITH store_history AS (
    SELECT
        region,
        month,
        store_id,

        CASE
            WHEN store_vs_nz_gap_pp < 0 THEN 1
            ELSE 0
        END AS store_below_benchmark,

        SUM(
            CASE
                WHEN store_vs_nz_gap_pp >= 0 THEN 1
                ELSE 0
            END
        ) OVER (
            PARTITION BY store_id
            ORDER BY month
            ROWS BETWEEN UNBOUNDED PRECEDING
                     AND CURRENT ROW
        ) AS streak_group

    FROM nz_benchmark_contribution
),

store_streaks AS (
    SELECT
        region,
        month,
        store_id,

        CASE
            WHEN store_below_benchmark = 1 THEN
                SUM(store_below_benchmark) OVER (
                    PARTITION BY store_id, streak_group
                    ORDER BY month
                    ROWS BETWEEN UNBOUNDED PRECEDING
                             AND CURRENT ROW
                )
            ELSE 0
        END AS store_below_benchmark_streak

    FROM store_history
),

store_contribution AS (
    SELECT
        s.*,
        h.store_below_benchmark_streak

    FROM nz_benchmark_contribution s

    JOIN store_streaks h
      ON s.region = h.region
     AND s.month = h.month
     AND s.store_id = h.store_id
),

regional_trends AS (
    SELECT
        region,
        month,
        benchmark_gap_pp,
        mom_margin_change_pp,
        rolling_3m_gp_margin_pct,
        below_benchmark_streak

    FROM profitability_trends
),

category_ranked AS (
    SELECT
        region,
        month,
        category,
        total_effect_pp,

        ROW_NUMBER() OVER (
            PARTITION BY region, month
            ORDER BY total_effect_pp ASC, category
        ) AS category_rank

    FROM category_margin_drivers
),

regional_category_context AS (
    SELECT
        region,
        month,
        category AS top_negative_category,
        total_effect_pp AS category_effect_pp

    FROM category_ranked

    WHERE category_rank = 1
),

combined AS (
    SELECT
        s.region,
        s.month,
        s.store_id,

        -- Store financial metrics
        s.net_sales_cents,
        s.gross_profit_cents,
        s.store_gp_margin_pct,
        s.nz_gp_margin_pct,

        -- Store benchmark analysis
        s.store_vs_nz_gap_pp,
        s.contribution_to_region_gap_pp,
        s.gp_shortfall_vs_nz_nzd,

        -- Store-specific persistence
        s.store_below_benchmark_streak,

        -- Regional trend context
        t.benchmark_gap_pp AS region_benchmark_gap_pp,
        t.mom_margin_change_pp AS region_mom_change_pp,
        t.rolling_3m_gp_margin_pct
            AS region_rolling_3m_margin_pct,
        t.below_benchmark_streak
            AS region_below_benchmark_streak,

        -- Regional category context
        c.top_negative_category,
        c.category_effect_pp,

        CASE
            WHEN s.store_vs_nz_gap_pp < 0 THEN 1
            ELSE 0
        END AS store_below_nz_benchmark,

        CASE
            WHEN t.mom_margin_change_pp < 0 THEN 1
            ELSE 0
        END AS region_margin_declining

    FROM store_contribution s

    JOIN regional_trends t
      ON s.region = t.region
     AND s.month = t.month

    LEFT JOIN regional_category_context c
      ON s.region = c.region
     AND s.month = c.month
),


ranked AS (
    SELECT
        *,

        -- National investigation rank based on
        -- signed hypothetical GP shortfall in NZD.
        -- Larger positive shortfalls rank first.
        ROW_NUMBER() OVER (
            PARTITION BY month
            ORDER BY
                gp_shortfall_vs_nz_nzd DESC,
                store_id ASC
        ) AS national_investigation_rank

    FROM combined
)


SELECT
    *,

    CASE
        WHEN store_below_nz_benchmark = 1
             AND contribution_to_region_gap_pp < 0
             AND store_below_benchmark_streak >= 3
             AND region_below_benchmark_streak >= 3
             AND region_margin_declining = 1
        THEN 'High'

        WHEN store_below_nz_benchmark = 1
             AND contribution_to_region_gap_pp < 0
        THEN 'Medium'

        ELSE 'Monitor'
    END AS investigation_priority

FROM ranked

ORDER BY
    month,
    national_investigation_rank;
