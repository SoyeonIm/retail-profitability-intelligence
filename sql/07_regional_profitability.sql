
-- Regional Profitability Mart
-- Grain: one row per region per month.
--
-- Dependency:
-- Create the store_performance DuckDB view from
-- sql/06_store_performance.sql before running.
--
-- Financial values are stored in integer NZD cents.
-- Regional GP margin = regional GP / regional net sales.
-- Benchmark = all-store weighted GP margin.
--
-- Synthetic data: regional comparisons are descriptive,
-- not evidence of real-world regional performance.

WITH region_month AS (
    SELECT
        region,
        month,
        COUNT(DISTINCT store_id) AS store_count,

        SUM(net_sales_cents) AS net_sales_cents,
        SUM(cogs_cents) AS cogs_cents,
        SUM(gross_profit_cents) AS gross_profit_cents,

        SUM(sale_lines) AS sale_lines,
        SUM(return_lines) AS return_lines,
        SUM(sale_discount_cents) AS sale_discount_cents

    FROM store_performance
    GROUP BY region, month
),

monthly_totals AS (
    SELECT
        month,
        SUM(net_sales_cents) AS nz_sales_cents,
        SUM(gross_profit_cents) AS nz_gp_cents
    FROM region_month
    GROUP BY month
),

regional_metrics AS (
    SELECT
        rm.region,
        rm.month,
        rm.store_count,

        rm.net_sales_cents,
        rm.cogs_cents,
        rm.gross_profit_cents,
        rm.sale_lines,
        rm.return_lines,
        rm.sale_discount_cents,

        ROUND(
            100.0 * rm.gross_profit_cents
            / NULLIF(rm.net_sales_cents, 0),
            4
        ) AS regional_gp_margin_pct,

        ROUND(
            100.0 * mt.nz_gp_cents
            / NULLIF(mt.nz_sales_cents, 0),
            4
        ) AS nz_gp_margin_pct,

        ROUND(
            100.0 * rm.gross_profit_cents
            / NULLIF(rm.net_sales_cents, 0)
            -
            100.0 * mt.nz_gp_cents
            / NULLIF(mt.nz_sales_cents, 0),
            4
        ) AS margin_variance_pp,

        ROUND(
            100.0 * rm.net_sales_cents
            / NULLIF(mt.nz_sales_cents, 0),
            6
        ) AS sales_contribution_pct,

        ROUND(
            100.0 * rm.gross_profit_cents
            / NULLIF(mt.nz_gp_cents, 0),
            6
        ) AS gp_contribution_pct

    FROM region_month rm
    INNER JOIN monthly_totals mt
        ON rm.month = mt.month
)

SELECT
    *,
    RANK() OVER (
        PARTITION BY month
        ORDER BY regional_gp_margin_pct DESC NULLS LAST
    ) AS regional_gp_margin_rank

FROM regional_metrics
ORDER BY month, region;
