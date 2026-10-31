
-- Store-level profitability diagnostics
-- Grain: store x month
-- Dependencies: store_performance
-- Financial amounts in integer NZD cents
-- Benchmark: sales-weighted regional GP margin

WITH store_base AS (
    SELECT
        region,
        month,
        store_id,
        net_sales_cents,
        gross_profit_cents,

        100.0 * gross_profit_cents::DOUBLE
            / NULLIF(net_sales_cents, 0)
            AS store_gp_margin_pct

    FROM store_performance
    WHERE net_sales_cents > 0
),

region_base AS (
    SELECT
        region,
        month,
        SUM(net_sales_cents) AS region_sales_cents,
        SUM(gross_profit_cents) AS region_gp_cents,

        100.0 * SUM(gross_profit_cents)::DOUBLE
            / NULLIF(SUM(net_sales_cents), 0)
            AS region_gp_margin_pct

    FROM store_base
    GROUP BY region, month
),

diagnostics AS (
    SELECT
        s.*,
        r.region_sales_cents,
        r.region_gp_cents,
        r.region_gp_margin_pct,

        100.0 * s.net_sales_cents::DOUBLE
            / NULLIF(r.region_sales_cents, 0)
            AS sales_contribution_pct,

        s.store_gp_margin_pct - r.region_gp_margin_pct
            AS margin_gap_pp,

        (
            s.net_sales_cents::DOUBLE
            / NULLIF(r.region_sales_cents, 0)
        ) * (
            s.store_gp_margin_pct - r.region_gp_margin_pct
        ) AS gp_gap_impact_pp,

        (
            s.net_sales_cents::DOUBLE
            * r.region_gp_margin_pct / 100.0
            - s.gross_profit_cents
        ) AS gp_shortfall_cents

    FROM store_base s
    JOIN region_base r
      ON s.region = r.region
     AND s.month = r.month
),

ranked AS (
    SELECT
        *,

        ROW_NUMBER() OVER (
            PARTITION BY region, month
            ORDER BY gp_shortfall_cents DESC, store_id
        ) AS shortfall_rank,

        ROW_NUMBER() OVER (
            PARTITION BY region, month
            ORDER BY gp_gap_impact_pp ASC, store_id
        ) AS negative_impact_rank

    FROM diagnostics
)

SELECT
    region,
    month,
    store_id,

    net_sales_cents,
    gross_profit_cents,
    region_sales_cents,
    region_gp_cents,

    ROUND(store_gp_margin_pct, 6)
        AS store_gp_margin_pct,

    ROUND(region_gp_margin_pct, 6)
        AS region_gp_margin_pct,

    ROUND(margin_gap_pp, 6)
        AS margin_gap_pp,

    ROUND(sales_contribution_pct, 6)
        AS sales_contribution_pct,

    ROUND(gp_gap_impact_pp, 6)
        AS gp_gap_impact_pp,

    ROUND(gp_shortfall_cents, 6)
        AS gp_shortfall_cents,

    ROUND(gp_shortfall_cents / 100.0, 2)
        AS gp_shortfall_nzd,

    shortfall_rank,
    negative_impact_rank

FROM ranked
ORDER BY month, region, shortfall_rank;
