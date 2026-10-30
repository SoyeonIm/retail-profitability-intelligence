# Transaction-level sales | Design notes

## Purpose
The original store-month dataset was independently simulated. This v1 sales engine creates a separate transaction-derived reporting path. **Its totals are not expected to reconcile to the original baseline**. Do not combine their sales totals or present their differences as operational variances.

## Grain and assumptions
- `transaction_line_id` uniquely identifies a row. In v1, each simulated sale line has its own `transaction_id`; basket-level grouping is deferred.
- Currency: NZD, excluding GST. Amounts are stored in integer cents.
- Sales: positive quantity, net sales and COGS. Discounts are positive.
- Returns: negative quantity, discount, net sales and COGS; every return references a sale line and reverses it completely.
- Returns are same-day and full-line in v1. This is a modelling simplification, not a claim about retail operations.
- Store opening dates constrain generated transactions. A store opened after the configured reporting window has no sales.
- Sale frequency is fixed per active store-month, with 120 sale lines by default. It is a prototype workload, not a calibrated transaction volume model.
- Product selection is uniform in v1. Consequently category sales mix is driven primarily by product counts and random sampling; this version **cannot support a realistic causal explanation of store margin differences**.
- Promotional discounts are sampled from a documented discrete distribution. Return probability is 2.5% per sale line.

## Reconciliation contract
At store-month grain: `gross_profit_cents = net_sales_cents - cogs_cents`. All transaction lines, including returns, are summed. `transaction_month_reconciliation.csv` is generated from `transactions.csv`, not independently simulated. The next step will build SQL assertions that compare this aggregation with a DuckDB mart.

## Known limitations and next improvements
Add realistic basket grouping, category/store preferences, price and cost changes, delayed/partial returns, and a store-month cost fact. Do not use v1 outputs to claim an observed real-world margin driver. Keep the original monthly baseline separate until the new model is fully validated.
