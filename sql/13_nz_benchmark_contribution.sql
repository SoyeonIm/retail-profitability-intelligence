
-- NZ benchmark contribution analysis
-- Grain: store x month
-- Benchmark: NZ-wide weighted GP margin by month
-- Contribution unit: percentage points (pp)
-- Financial amounts: NZD cents

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

nz_monthly AS (
    SELECT
        month,
        SUM(net_sales_cents) AS nz_sales_cents,
        SUM(gross_profit_cents) AS nz_gp_cents,

        100.0 * SUM(gross_profit_cents)::DOUBLE
            / NULLIF(SUM(net_sales_cents), 0)
            AS nz_gp_margin_pct

    FROM store_base
    GROUP BY month
),

region_monthly AS (
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

contributions AS (
    SELECT
        s.*,
        n.nz_sales_cents,
        n.nz_gp_cents,
        n.nz_gp_margin_pct,
        r.region_sales_cents,
        r.region_gp_cents,
        r.region_gp_margin_pct,

        s.store_gp_margin_pct - n.nz_gp_margin_pct
            AS store_vs_nz_gap_pp,

        r.region_gp_margin_pct - n.nz_gp_margin_pct
            AS region_vs_nz_gap_pp,

        100.0 * s.net_sales_cents::DOUBLE
            / NULLIF(r.region_sales_cents, 0)
            AS region_sales_share_pct,

        (
            s.net_sales_cents::DOUBLE
            / NULLIF(r.region_sales_cents, 0)
        ) * (
            s.store_gp_margin_pct - n.nz_gp_margin_pct
        ) AS contribution_to_region_gap_pp,

        (
            s.net_sales_cents::DOUBLE
            * n.nz_gp_margin_pct / 100.0
            - s.gross_profit_cents
        ) AS gp_shortfall_vs_nz_cents

    FROM store_base s
    JOIN nz_monthly n
      ON s.month = n.month
    JOIN region_monthly r
      ON s.region = r.region
     AND s.month = r.month
),

ranked AS (
    SELECT
        *,

        ROW_NUMBER() OVER (
            PARTITION BY region, month
            ORDER BY contribution_to_region_gap_pp ASC, store_id
        ) AS negative_contribution_rank

    FROM contributions
)

SELECT
    region,
    month,
    store_id,

    net_sales_cents,
    gross_profit_cents,
    region_sales_cents,
    region_gp_cents,
    nz_sales_cents,
    nz_gp_cents,

    ROUND(store_gp_margin_pct, 6)
        AS store_gp_margin_pct,

    ROUND(region_gp_margin_pct, 6)
        AS region_gp_margin_pct,

    ROUND(nz_gp_margin_pct, 6)
        AS nz_gp_margin_pct,

    ROUND(store_vs_nz_gap_pp, 6)
        AS store_vs_nz_gap_pp,

    ROUND(region_vs_nz_gap_pp, 6)
        AS region_vs_nz_gap_pp,

    ROUND(region_sales_share_pct, 6)
        AS region_sales_share_pct,

    ROUND(contribution_to_region_gap_pp, 6)
        AS contribution_to_region_gap_pp,

    ROUND(gp_shortfall_vs_nz_cents, 6)
        AS gp_shortfall_vs_nz_cents,

    ROUND(gp_shortfall_vs_nz_cents / 100.0, 2)
        AS gp_shortfall_vs_nz_nzd,

    negative_contribution_rank

FROM ranked
ORDER BY month, region, negative_contribution_rank;
