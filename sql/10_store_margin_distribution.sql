
-- Store-level GP margin distribution by region and month
-- Grain: region x month
-- Dependency: store_performance

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

region_stats AS (
    SELECT
        region,
        month,
        COUNT(*) AS store_count,
        SUM(net_sales_cents)::BIGINT AS region_sales_cents,
        SUM(gross_profit_cents)::BIGINT AS region_gp_cents,

        100.0 * SUM(gross_profit_cents)::DOUBLE
            / NULLIF(SUM(net_sales_cents), 0)
            AS weighted_gp_margin_pct,

        AVG(store_gp_margin_pct) AS mean_store_gp_margin_pct,
        MEDIAN(store_gp_margin_pct) AS median_store_gp_margin_pct,
        QUANTILE_CONT(store_gp_margin_pct, 0.25) AS p25_gp_margin_pct,
        QUANTILE_CONT(store_gp_margin_pct, 0.75) AS p75_gp_margin_pct,

        MIN(store_gp_margin_pct) AS min_gp_margin_pct,
        MAX(store_gp_margin_pct) AS max_gp_margin_pct,
        STDDEV_SAMP(store_gp_margin_pct) AS stddev_gp_margin_pp
    FROM store_base
    GROUP BY region, month
),

store_comparison AS (
    SELECT
        s.region,
        s.month,
        s.store_id,
        s.store_gp_margin_pct,
        r.weighted_gp_margin_pct,

        CASE
            WHEN s.store_gp_margin_pct < r.weighted_gp_margin_pct
            THEN 1 ELSE 0
        END AS below_weighted_average,

        CASE
            WHEN s.store_gp_margin_pct < r.median_store_gp_margin_pct
            THEN 1 ELSE 0
        END AS below_median
    FROM store_base s
    JOIN region_stats r
      ON s.region = r.region
     AND s.month = r.month
),

distribution_counts AS (
    SELECT
        region,
        month,
        SUM(below_weighted_average) AS stores_below_weighted_avg,
        SUM(below_median) AS stores_below_median
    FROM store_comparison
    GROUP BY region, month
),

ranked_stores AS (
    SELECT
        *,
        ROW_NUMBER() OVER (
            PARTITION BY region, month
            ORDER BY store_gp_margin_pct DESC, store_id
        ) AS highest_rank,

        ROW_NUMBER() OVER (
            PARTITION BY region, month
            ORDER BY store_gp_margin_pct ASC, store_id
        ) AS lowest_rank
    FROM store_base
),

extreme_stores AS (
    SELECT
        region,
        month,
        MAX(
            CASE WHEN highest_rank = 1 THEN store_id END
        ) AS highest_margin_store_id,
        MAX(
            CASE WHEN lowest_rank = 1 THEN store_id END
        ) AS lowest_margin_store_id
    FROM ranked_stores
    GROUP BY region, month
)

SELECT
    r.region,
    r.month,
    r.store_count,
    r.region_sales_cents,
    r.region_gp_cents,

    ROUND(r.weighted_gp_margin_pct, 6)
        AS weighted_gp_margin_pct,
    ROUND(r.mean_store_gp_margin_pct, 6)
        AS mean_store_gp_margin_pct,
    ROUND(r.median_store_gp_margin_pct, 6)
        AS median_store_gp_margin_pct,
    ROUND(r.p25_gp_margin_pct, 6)
        AS p25_gp_margin_pct,
    ROUND(r.p75_gp_margin_pct, 6)
        AS p75_gp_margin_pct,
    ROUND(
        r.p75_gp_margin_pct - r.p25_gp_margin_pct, 6
    ) AS iqr_gp_margin_pp,
    ROUND(r.min_gp_margin_pct, 6)
        AS min_gp_margin_pct,
    ROUND(r.max_gp_margin_pct, 6)
        AS max_gp_margin_pct,
    ROUND(r.stddev_gp_margin_pp, 6)
        AS stddev_gp_margin_pp,

    d.stores_below_weighted_avg,
    d.stores_below_median,

    e.highest_margin_store_id,
    e.lowest_margin_store_id

FROM region_stats r
JOIN distribution_counts d
  ON r.region = d.region
 AND r.month = d.month
JOIN extreme_stores e
  ON r.region = e.region
 AND r.month = e.month
ORDER BY r.month, r.region;
