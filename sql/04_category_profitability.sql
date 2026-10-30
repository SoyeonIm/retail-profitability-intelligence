
-- Store-category-month profitability mart
-- Monetary amounts are stored as integer NZD cents.

WITH transaction_enriched AS (
    SELECT
        t.transaction_line_id,
        t.store_id,
        DATE_TRUNC('month', CAST(t.transaction_date AS DATE))::DATE AS month,
        p.category,
        t.transaction_type,
        t.quantity,
        t.net_sales_cents,
        t.cogs_cents,
        CASE
            WHEN t.transaction_type = 'SALE'
            THEN t.discount_cents
            ELSE 0
        END AS sale_discount_cents
    FROM read_csv_auto('data/raw/transactions.csv') t
    INNER JOIN read_csv_auto('data/raw/products.csv') p
        ON t.product_id = p.product_id
),
category_month AS (
    SELECT
        store_id,
        month,
        category,
        COUNT(*) AS transaction_lines,
        SUM(CASE WHEN transaction_type = 'SALE' THEN 1 ELSE 0 END) AS sale_lines,
        SUM(CASE WHEN transaction_type = 'RETURN' THEN 1 ELSE 0 END) AS return_lines,
        SUM(net_sales_cents) AS net_sales_cents,
        SUM(cogs_cents) AS cogs_cents,
        SUM(sale_discount_cents) AS sale_discount_cents
    FROM transaction_enriched
    GROUP BY store_id, month, category
)
SELECT
    store_id,
    month,
    category,
    transaction_lines,
    sale_lines,
    return_lines,
    net_sales_cents,
    cogs_cents,
    sale_discount_cents,
    net_sales_cents - cogs_cents AS gross_profit_cents,
    ROUND(
        100.0 * (net_sales_cents - cogs_cents)
        / NULLIF(net_sales_cents, 0),
        2
    ) AS gp_margin_pct
FROM category_month
ORDER BY store_id, month, category;
