
-- Category-level regional margin drivers
-- Grain: region x month x category
-- Benchmark: NZ sales-weighted category margins
-- Currency: integer NZD cents
-- Effects: percentage points
-- Dependency: category_mart

WITH store_dimension AS (
    SELECT
        store_id,
        region
    FROM read_csv_auto('data/raw/stores.csv')
),

region_category AS (
    SELECT
        s.region,
        c.month,
        c.category,
        SUM(c.net_sales_cents)::BIGINT AS sales_cents,
        SUM(c.gross_profit_cents)::BIGINT AS gp_cents
    FROM category_mart c
    INNER JOIN store_dimension s
        ON c.store_id = s.store_id
    GROUP BY
        s.region, c.month, c.category
),

region_totals AS (
    SELECT
        region,
        month,
        SUM(sales_cents)::BIGINT AS region_sales_cents,
        SUM(gp_cents)::BIGINT AS region_gp_cents
    FROM region_category
    GROUP BY region, month
),

benchmark_category AS (
    SELECT
        month,
        category,
        SUM(sales_cents)::BIGINT AS benchmark_category_sales_cents,
        SUM(gp_cents)::BIGINT AS benchmark_category_gp_cents
    FROM region_category
    GROUP BY month, category
),

benchmark_totals AS (
    SELECT
        month,
        SUM(benchmark_category_sales_cents)::BIGINT
            AS benchmark_sales_cents,
        SUM(benchmark_category_gp_cents)::BIGINT
            AS benchmark_gp_cents
    FROM benchmark_category
    GROUP BY month
),

category_grid AS (
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

metrics AS (
    SELECT
        g.region,
        g.month,
        g.category,

        COALESCE(rc.sales_cents, 0)::BIGINT
            AS category_sales_cents,
        COALESCE(rc.gp_cents, 0)::BIGINT
            AS category_gp_cents,

        rt.region_sales_cents,
        rt.region_gp_cents,

        bc.benchmark_category_sales_cents,
        bc.benchmark_category_gp_cents,
        bt.benchmark_sales_cents,
        bt.benchmark_gp_cents,

        COALESCE(rc.sales_cents, 0)::DOUBLE
            / NULLIF(rt.region_sales_cents, 0)
            AS region_sales_mix,

        bc.benchmark_category_sales_cents::DOUBLE
            / NULLIF(bt.benchmark_sales_cents, 0)
            AS benchmark_sales_mix,

        bc.benchmark_category_gp_cents::DOUBLE
            / NULLIF(bc.benchmark_category_sales_cents, 0)
            AS benchmark_category_margin,

        CASE
            WHEN COALESCE(rc.sales_cents, 0) > 0
            THEN rc.gp_cents::DOUBLE / rc.sales_cents
            ELSE NULL
        END AS region_category_margin

    FROM category_grid g

    LEFT JOIN region_category rc
        ON g.region = rc.region
        AND g.month = rc.month
        AND g.category = rc.category

    INNER JOIN region_totals rt
        ON g.region = rt.region
        AND g.month = rt.month

    INNER JOIN benchmark_category bc
        ON g.month = bc.month
        AND g.category = bc.category

    INNER JOIN benchmark_totals bt
        ON g.month = bt.month
),

effects AS (
    SELECT
        *,
        (
            region_sales_mix - benchmark_sales_mix
        ) * benchmark_category_margin
            AS mix_effect,

        CASE
            WHEN category_sales_cents > 0
            THEN region_sales_mix * (
                region_category_margin
                - benchmark_category_margin
            )
            ELSE 0.0
        END AS margin_effect
    FROM metrics
)

SELECT
    region,
    month,
    category,

    category_sales_cents,
    category_gp_cents,
    region_sales_cents,
    region_gp_cents,
    benchmark_category_sales_cents,
    benchmark_category_gp_cents,
    benchmark_sales_cents,
    benchmark_gp_cents,

    ROUND(100.0 * region_sales_mix, 6)
        AS region_sales_mix_pct,

    ROUND(100.0 * benchmark_sales_mix, 6)
        AS benchmark_sales_mix_pct,

    ROUND(100.0 * region_category_margin, 6)
        AS region_category_margin_pct,

    ROUND(100.0 * benchmark_category_margin, 6)
        AS benchmark_category_margin_pct,

    ROUND(100.0 * mix_effect, 6)
        AS mix_effect_pp,

    ROUND(100.0 * margin_effect, 6)
        AS margin_effect_pp,

    ROUND(100.0 * (mix_effect + margin_effect), 6)
        AS total_effect_pp

FROM effects
ORDER BY month, region, category;
