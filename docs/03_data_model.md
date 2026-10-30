# Retail profitability | Data model (proposed)

## Decision and grain

The first deliverable is a reliable store-month profitability comparison. The current dataset has one store record per store and one financial record per store-month. A transaction-level sales model will be introduced only after its generation and reconciliation rules are specified and tested.

| Table | Grain | Key | Status |
|---|---|---|---|
| `dim_store` | One row per store | `store_id` | Implemented |
| `fact_store_month` | One row per store-month | (`store_id`, `month`) | Implemented |
| `dim_product` | One row per product | `product_id` | Proposed |
| `dim_date` | One row per calendar date | `date_id` | Proposed |
| `fact_sales` | One row per transaction line | `transaction_line_id` | Proposed |
| `fact_store_month_cost` | One row per store-month | (`store_id`, `month`) | Proposed |
| `mart_store_profitability` | One row per store-month | (`store_id`, `month`) | Proposed |

## Financial definitions

All amounts are NZD excluding GST. Gross profit = net sales - cost of goods sold. GP margin = SUM(gross profit) / SUM(net sales), not the average of individual percentages. Store contribution = gross profit - labour - occupancy - other store costs; it is not statutory net profit.

## Join contract

Never join transaction-level sales directly to store-month costs and sum the result. First aggregate sales to (`store_id`, `month`), then join to costs at the same grain. Check key uniqueness and reconcile totals before and after the join.

## Existing-data caveat

The first synthetic generator assigns opening years independently of the financial reporting period and produces financial records for every store in every month. This can create pre-opening sales. The baseline audit measures the problem; later revisions will correct the generation logic. Until then, do not treat store rankings as business findings.

## Model design decision

Preserve the baseline generator and tables for reproducibility while building the transaction-level model in separate scripts. Once the new model passes reconciliation checks, retire the baseline as a legacy fixture rather than silently replacing it.
