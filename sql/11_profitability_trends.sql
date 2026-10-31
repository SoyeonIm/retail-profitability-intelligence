
-- Regional profitability trends
-- Grain: region x month
-- Dependency: regional_profitability
-- Margin changes are percentage points (pp)
-- Rolling margins are calculated from financial totals

WITH monthly AS (
    SELECT
        region,
        month,
        net_sales_cents,
        gross_profit_cents,

        100.0 * gross_profit_cents::DOUBLE
            / NULLIF(net_sales_cents, 0)
            AS gp_margin_pct

    FROM regional_profitability
),

nz_monthly AS (
    SELECT
        month,
        SUM(net_sales_cents)::BIGINT AS nz_sales_cents,
        SUM(gross_profit_cents)::BIGINT AS nz_gp_cents,

        100.0 * SUM(gross_profit_cents)::DOUBLE
            / NULLIF(SUM(net_sales_cents), 0)
            AS nz_gp_margin_pct

    FROM monthly
    GROUP BY month
),

time_series AS (
    SELECT
        m.*,
        n.nz_gp_margin_pct,

        LAG(m.gp_margin_pct, 1) OVER (
            PARTITION BY m.region
            ORDER BY m.month
        ) AS previous_month_margin_pct,

        LAG(m.gp_margin_pct, 12) OVER (
            PARTITION BY m.region
            ORDER BY m.month
        ) AS previous_year_margin_pct,

        SUM(m.net_sales_cents) OVER (
            PARTITION BY m.region
            ORDER BY m.month
            ROWS BETWEEN 2 PRECEDING AND CURRENT ROW
        ) AS rolling_3m_sales_cents,

        SUM(m.gross_profit_cents) OVER (
            PARTITION BY m.region
            ORDER BY m.month
            ROWS BETWEEN 2 PRECEDING AND CURRENT ROW
        ) AS rolling_3m_gp_cents,

        COUNT(*) OVER (
            PARTITION BY m.region
            ORDER BY m.month
            ROWS BETWEEN 2 PRECEDING AND CURRENT ROW
        ) AS rolling_3m_month_count

    FROM monthly m
    JOIN nz_monthly n
      ON m.month = n.month
),

flagged AS (
    SELECT
        *,
        CASE
            WHEN gp_margin_pct < nz_gp_margin_pct
            THEN 1 ELSE 0
        END AS below_nz_benchmark,

        CASE
            WHEN gp_margin_pct < nz_gp_margin_pct
            THEN 0 ELSE 1
        END AS streak_reset
    FROM time_series
),

streak_groups AS (
    SELECT
        *,
        SUM(streak_reset) OVER (
            PARTITION BY region
            ORDER BY month
            ROWS BETWEEN UNBOUNDED PRECEDING
                 AND CURRENT ROW
        ) AS streak_group
    FROM flagged
),


streaks AS (
    SELECT
        *,
        CASE
            WHEN below_nz_benchmark = 1
            THEN SUM(below_nz_benchmark) OVER (
                PARTITION BY region, streak_group
                ORDER BY month
                ROWS BETWEEN UNBOUNDED PRECEDING
                     AND CURRENT ROW
            )
            ELSE 0
        END AS below_benchmark_streak
    FROM streak_groups
)


SELECT
    region,
    month,
    net_sales_cents,
    gross_profit_cents,

    ROUND(gp_margin_pct, 6) AS gp_margin_pct,
    ROUND(nz_gp_margin_pct, 6) AS nz_gp_margin_pct,

    ROUND(
        gp_margin_pct - nz_gp_margin_pct, 6
    ) AS benchmark_gap_pp,

    ROUND(
        gp_margin_pct - previous_month_margin_pct, 6
    ) AS mom_margin_change_pp,

    ROUND(
        gp_margin_pct - previous_year_margin_pct, 6
    ) AS yoy_margin_change_pp,

    rolling_3m_sales_cents,
    rolling_3m_gp_cents,
    rolling_3m_month_count,

    CASE
        WHEN rolling_3m_month_count = 3
        THEN ROUND(
            100.0 * rolling_3m_gp_cents::DOUBLE
                / NULLIF(rolling_3m_sales_cents, 0),
            6
        )
        ELSE NULL
    END AS rolling_3m_gp_margin_pct,

    below_nz_benchmark,
    below_benchmark_streak

FROM streaks
ORDER BY region, month;
