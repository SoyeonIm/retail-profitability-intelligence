
-- Store Performance Mart
-- Grain: one row per store per month.
--
-- Dependency:
-- A DuckDB view named category_mart must be created
-- from sql/04_category_profitability.sql before running.
--
-- All financial totals are aggregated in integer NZD cents.
-- Benchmark margins are sales-weighted across all stores.
-- This is synthetic data; rankings are descriptive only.

WITH store_month AS (
    SELECT
        store_id,
        month,
        SUM(transaction_lines) AS transaction_lines,
        SUM(sale_lines) AS sale_lines,
        SUM(return_lines) AS return_lines,
        SUM(net_sales_cents) AS net_sales_cents,
        SUM(cogs_cents) AS cogs_cents,
        SUM(gross_profit_cents) AS gross_profit_cents,
        SUM(sale_discount_cents) AS sale_discount_cents
    FROM category_mart
    GROUP BY store_id, month
),

store_dimension AS (
    SELECT
        store_id,
        region,
        floor_area_sqm,
        open_date
    FROM read_csv_auto('data/raw/stores.csv')
),

monthly_benchmark AS (
    SELECT
        month,
        SUM(net_sales_cents) AS total_month_sales_cents,
        SUM(gross_profit_cents) AS total_month_gp_cents
    FROM store_month
    GROUP BY month
),

performance AS (
    SELECT
        sm.store_id,
        sd.region,
        sd.floor_area_sqm,
        sd.open_date,
        sm.month,

        sm.transaction_lines,
        sm.sale_lines,
        sm.return_lines,

        sm.net_sales_cents,
        sm.cogs_cents,
        sm.gross_profit_cents,
        sm.sale_discount_cents,

        ROUND(
            100.0 * sm.gross_profit_cents
            / NULLIF(sm.net_sales_cents, 0),
            4
        ) AS gp_margin_pct,

        ROUND(
            100.0 * mb.total_month_gp_cents
            / NULLIF(mb.total_month_sales_cents, 0),
            4
        ) AS benchmark_gp_margin_pct,

        ROUND(
            100.0 * sm.gross_profit_cents
            / NULLIF(sm.net_sales_cents, 0)
            -
            100.0 * mb.total_month_gp_cents
            / NULLIF(mb.total_month_sales_cents, 0),
            4
        ) AS margin_variance_pp,

        ROUND(
            100.0 * sm.net_sales_cents
            / NULLIF(mb.total_month_sales_cents, 0),
            6
        ) AS sales_share_pct,

        ROUND(
            100.0 * sm.gross_profit_cents
            / NULLIF(mb.total_month_gp_cents, 0),
            6
        ) AS gp_contribution_pct,

        ROUND(
            100.0 * sm.return_lines
            / NULLIF(sm.sale_lines, 0),
            4
        ) AS return_lines_per_100_sale_lines

    FROM store_month sm
    INNER JOIN store_dimension sd
        ON sm.store_id = sd.store_id
    INNER JOIN monthly_benchmark mb
        ON sm.month = mb.month
)

SELECT
    *,
    RANK() OVER (
        PARTITION BY month
        ORDER BY net_sales_cents DESC
    ) AS sales_rank,

    RANK() OVER (
        PARTITION BY month
        ORDER BY gross_profit_cents DESC
    ) AS gp_rank,

    RANK() OVER (
        PARTITION BY month
        ORDER BY gp_margin_pct DESC NULLS LAST
    ) AS gp_margin_rank

FROM performance
ORDER BY month, store_id;
