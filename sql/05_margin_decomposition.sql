
-- Store-level gross margin decomposition
-- Comparison: each store vs the all-store weighted benchmark
-- Grain: one row per store and month
-- Currency: NZD cents

WITH category_store AS (
    SELECT
        store_id,
        month,
        category,
        SUM(net_sales_cents)::BIGINT AS net_sales_cents,
        SUM(gross_profit_cents)::BIGINT AS gross_profit_cents
    FROM category_mart
    GROUP BY
        store_id,
        month,
        category
),

store_month_totals AS (
    SELECT
        store_id,
        month,
        SUM(net_sales_cents)::BIGINT AS store_sales_cents,
        SUM(gross_profit_cents)::BIGINT AS store_gp_cents
    FROM category_store
    GROUP BY store_id, month
),

benchmark_category AS (
    SELECT
        month,
        category,
        SUM(net_sales_cents)::BIGINT AS benchmark_sales_cents,
        SUM(gross_profit_cents)::BIGINT AS benchmark_gp_cents
    FROM category_store
    GROUP BY month, category
),

benchmark_month_totals AS (
    SELECT
        month,
        SUM(benchmark_sales_cents)::BIGINT AS benchmark_total_sales_cents,
        SUM(benchmark_gp_cents)::BIGINT AS benchmark_total_gp_cents
    FROM benchmark_category
    GROUP BY month
),

store_category_grid AS (
    SELECT
        s.store_id,
        s.month,
        b.category
    FROM store_month_totals s
    INNER JOIN (
        SELECT DISTINCT month, category
        FROM benchmark_category
    ) b
        ON s.month = b.month
),

category_effects AS (
    SELECT
        g.store_id,
        g.month,
        g.category,

        COALESCE(cs.net_sales_cents, 0)::BIGINT
            AS store_category_sales_cents,

        COALESCE(cs.gross_profit_cents, 0)::BIGINT
            AS store_category_gp_cents,

        sm.store_sales_cents,
        sm.store_gp_cents,

        bc.benchmark_sales_cents,
        bc.benchmark_gp_cents,

        bm.benchmark_total_sales_cents,
        bm.benchmark_total_gp_cents,

        (
            COALESCE(cs.net_sales_cents, 0)::DOUBLE
            / NULLIF(sm.store_sales_cents, 0)
        ) AS store_sales_mix,

        (
            bc.benchmark_sales_cents::DOUBLE
            / NULLIF(bm.benchmark_total_sales_cents, 0)
        ) AS benchmark_sales_mix,

        (
            bc.benchmark_gp_cents::DOUBLE
            / NULLIF(bc.benchmark_sales_cents, 0)
        ) AS benchmark_category_margin,

        CASE
            WHEN COALESCE(cs.net_sales_cents, 0) > 0
            THEN
                COALESCE(cs.gross_profit_cents, 0)::DOUBLE
                / cs.net_sales_cents
            ELSE NULL
        END AS store_category_margin

    FROM store_category_grid g

    LEFT JOIN category_store cs
        ON g.store_id = cs.store_id
        AND g.month = cs.month
        AND g.category = cs.category

    INNER JOIN store_month_totals sm
        ON g.store_id = sm.store_id
        AND g.month = sm.month

    INNER JOIN benchmark_category bc
        ON g.month = bc.month
        AND g.category = bc.category

    INNER JOIN benchmark_month_totals bm
        ON g.month = bm.month
),

decomposition AS (
    SELECT
        *,

        (
            (store_sales_mix - benchmark_sales_mix)
            * benchmark_category_margin
        ) AS mix_effect,

        CASE
            WHEN store_category_sales_cents > 0
            THEN
                store_sales_mix
                * (
                    store_category_margin
                    - benchmark_category_margin
                )
            ELSE 0.0
        END AS margin_effect

    FROM category_effects
),

store_summary AS (
    SELECT
        store_id,
        month,

        MAX(store_sales_cents) AS store_sales_cents,
        MAX(store_gp_cents) AS store_gp_cents,

        MAX(benchmark_total_sales_cents)
            AS benchmark_total_sales_cents,

        MAX(benchmark_total_gp_cents)
            AS benchmark_total_gp_cents,

        SUM(mix_effect) AS mix_effect,
        SUM(margin_effect) AS margin_effect

    FROM decomposition
    GROUP BY store_id, month
)

SELECT
    store_id,
    month,

    store_sales_cents,
    store_gp_cents,

    benchmark_total_sales_cents,
    benchmark_total_gp_cents,

    ROUND(
        100.0 * store_gp_cents
        / NULLIF(store_sales_cents, 0),
        4
    ) AS store_gp_margin_pct,

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
            (
                store_gp_cents::DOUBLE
                / NULLIF(store_sales_cents, 0)
            )
            -
            (
                benchmark_total_gp_cents::DOUBLE
                / NULLIF(benchmark_total_sales_cents, 0)
            )
        ),
        6
    ) AS actual_gap_pp,

    ROUND(
        100.0 * (
            (
                store_gp_cents::DOUBLE
                / NULLIF(store_sales_cents, 0)
            )
            -
            (
                benchmark_total_gp_cents::DOUBLE
                / NULLIF(benchmark_total_sales_cents, 0)
            )
            - mix_effect
            - margin_effect
        ),
        10
    ) AS reconciliation_residual_pp

FROM store_summary
ORDER BY month, store_id;
