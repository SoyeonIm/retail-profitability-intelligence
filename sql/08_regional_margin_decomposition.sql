
-- Regional gross margin decomposition
-- Comparison: each region vs NZ all-store weighted benchmark
-- Grain: one row per region and month
-- Currency: integer NZD cents
--
-- Dependency: category_mart view from
-- sql/04_category_profitability.sql
--
-- This is an accounting decomposition, not causal inference.

WITH category_region AS (
    SELECT
        s.region,
        c.month,
        c.category,
        SUM(c.net_sales_cents)::BIGINT AS sales_cents,
        SUM(c.gross_profit_cents)::BIGINT AS gp_cents
    FROM category_mart c
    INNER JOIN read_csv_auto('data/raw/stores.csv') s
        ON c.store_id = s.store_id
    GROUP BY s.region, c.month, c.category
),

region_totals AS (
    SELECT
        region,
        month,
        SUM(sales_cents)::BIGINT AS region_sales_cents,
        SUM(gp_cents)::BIGINT AS region_gp_cents
    FROM category_region
    GROUP BY region, month
),

benchmark_category AS (
    SELECT
        month,
        category,
        SUM(sales_cents)::BIGINT AS benchmark_sales_cents,
        SUM(gp_cents)::BIGINT AS benchmark_gp_cents
    FROM category_region
    GROUP BY month, category
),

benchmark_totals AS (
    SELECT
        month,
        SUM(benchmark_sales_cents)::BIGINT
            AS benchmark_sales_cents,
        SUM(benchmark_gp_cents)::BIGINT
            AS benchmark_gp_cents
    FROM benchmark_category
    GROUP BY month
),

region_category_grid AS (
    SELECT
        r.region,
        r.month,
        b.category
    FROM region_totals r
    INNER JOIN (
        SELECT DISTINCT month, category
        FROM benchmark_category
    ) b
        ON r.month = b.month
),

category_metrics AS (
    SELECT
        g.region,
        g.month,
        g.category,

        COALESCE(cr.sales_cents, 0)::BIGINT
            AS category_sales_cents,

        COALESCE(cr.gp_cents, 0)::BIGINT
            AS category_gp_cents,

        rt.region_sales_cents,
        rt.region_gp_cents,

        bc.benchmark_sales_cents
            AS benchmark_category_sales_cents,

        bc.benchmark_gp_cents
            AS benchmark_category_gp_cents,

        bt.benchmark_sales_cents
            AS benchmark_total_sales_cents,

        bt.benchmark_gp_cents
            AS benchmark_total_gp_cents,

        COALESCE(cr.sales_cents, 0)::DOUBLE
            / NULLIF(rt.region_sales_cents, 0)
            AS region_mix,

        bc.benchmark_sales_cents::DOUBLE
            / NULLIF(bt.benchmark_sales_cents, 0)
            AS benchmark_mix,

        bc.benchmark_gp_cents::DOUBLE
            / NULLIF(bc.benchmark_sales_cents, 0)
            AS benchmark_category_margin,

        CASE
            WHEN COALESCE(cr.sales_cents, 0) > 0
            THEN cr.gp_cents::DOUBLE / cr.sales_cents
            ELSE NULL
        END AS region_category_margin

    FROM region_category_grid g

    LEFT JOIN category_region cr
        ON g.region = cr.region
        AND g.month = cr.month
        AND g.category = cr.category

    INNER JOIN region_totals rt
        ON g.region = rt.region
        AND g.month = rt.month

    INNER JOIN benchmark_category bc
        ON g.month = bc.month
        AND g.category = bc.category

    INNER JOIN benchmark_totals bt
        ON g.month = bt.month
),

category_effects AS (
    SELECT
        *,
        (
            (region_mix - benchmark_mix)
            * benchmark_category_margin
        ) AS mix_effect,

        CASE
            WHEN category_sales_cents > 0
            THEN region_mix * (
                region_category_margin
                - benchmark_category_margin
            )
            ELSE 0.0
        END AS margin_effect

    FROM category_metrics
),

region_summary AS (
    SELECT
        region,
        month,

        MAX(region_sales_cents) AS region_sales_cents,
        MAX(region_gp_cents) AS region_gp_cents,

        MAX(benchmark_total_sales_cents)
            AS benchmark_total_sales_cents,

        MAX(benchmark_total_gp_cents)
            AS benchmark_total_gp_cents,

        SUM(mix_effect) AS mix_effect,
        SUM(margin_effect) AS margin_effect

    FROM category_effects
    GROUP BY region, month
)

SELECT
    region,
    month,

    region_sales_cents,
    region_gp_cents,

    benchmark_total_sales_cents,
    benchmark_total_gp_cents,

    ROUND(
        100.0 * region_gp_cents
        / NULLIF(region_sales_cents, 0),
        4
    ) AS regional_gp_margin_pct,

    ROUND(
        100.0 * benchmark_total_gp_cents
        / NULLIF(benchmark_total_sales_cents, 0),
        4
    ) AS benchmark_gp_margin_pct,

    ROUND(100.0 * mix_effect, 6)
        AS mix_effect_pp,

    ROUND(100.0 * margin_effect, 6)
        AS margin_effect_pp,

    ROUND(
        100.0 * (mix_effect + margin_effect),
        6
    ) AS explained_gap_pp,

    ROUND(
        100.0 * (
            region_gp_cents::DOUBLE
            / NULLIF(region_sales_cents, 0)
            -
            benchmark_total_gp_cents::DOUBLE
            / NULLIF(benchmark_total_sales_cents, 0)
        ),
        6
    ) AS actual_gap_pp,

    ROUND(
        100.0 * (
            region_gp_cents::DOUBLE
            / NULLIF(region_sales_cents, 0)
            -
            benchmark_total_gp_cents::DOUBLE
            / NULLIF(benchmark_total_sales_cents, 0)
            - mix_effect
            - margin_effect
        ),
        10
    ) AS reconciliation_residual_pp

FROM region_summary
ORDER BY month, region;
