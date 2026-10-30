
-- Transaction-level financial reconciliation
-- All monetary calculations use integer NZD cents.

WITH store_month_sales AS (
    SELECT
        store_id,
        DATE_TRUNC('month', CAST(transaction_date AS DATE))::DATE AS month,
        COUNT(*) AS transaction_lines,
        SUM(CASE WHEN transaction_type = 'SALE' THEN 1 ELSE 0 END) AS sale_lines,
        SUM(CASE WHEN transaction_type = 'RETURN' THEN 1 ELSE 0 END) AS return_lines,
        SUM(net_sales_cents) AS net_sales_cents,
        SUM(cogs_cents) AS cogs_cents
    FROM read_csv_auto('data/raw/transactions.csv')
    GROUP BY 1, 2
)
SELECT
    store_id,
    month,
    transaction_lines,
    sale_lines,
    return_lines,
    ROUND(net_sales_cents / 100.0, 2) AS net_sales_nzd,
    ROUND(cogs_cents / 100.0, 2) AS cogs_nzd,
    ROUND((net_sales_cents - cogs_cents) / 100.0, 2) AS gross_profit_nzd,
    ROUND(
        100.0 * (net_sales_cents - cogs_cents)
        / NULLIF(net_sales_cents, 0),
        2
    ) AS gp_margin_pct
FROM store_month_sales
ORDER BY store_id, month;
