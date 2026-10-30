# Retail profitability | Analysis charter

## Decision to support
Which stores warrant a closer profitability review, and what additional evidence would be required before management changes pricing, product mix or store operations?

## Scope
60 fictional NZ stores, Jan 2025–Sep 2026, at store-month grain. All financial figures are simulated; no company records are included.

## First analytical questions
1. Are gross margin differences material at store level, not just regional aggregates?
2. Does a ranking change when we compare similarly sized and similarly mature stores?
3. Which questions cannot be answered without product-level transactions and pricing data?

## Metric contract (v0)
- Net sales: simulated monthly revenue, NZD. No transaction-level gross-to-net reconciliation yet.
- COGS: simulated monthly cost of goods sold, NZD.
- Gross profit = net sales - COGS.
- GP margin = sum(gross profit) / sum(net sales), not average(store-month margin).
- Store contribution = gross profit - labour - occupancy - other store costs. This is not statutory operating profit.
- Cost ratios = sum(cost) / sum(net sales).

## Decision guardrails
- Regional comparisons are descriptive, not causal.
- The generator assigns each store a random baseline GP rate; it does not yet model category mix, pricing or discounting.
- The generator applies region factors to sales, not GP rate. Any regional GP pattern may reflect random store allocation.
- Stores are generated with opening years through 2025, and financial rows begin in Jan 2025 regardless of opening date. Filter pre-opening periods before claiming maturity or like-for-like comparisons.
- There are no product transactions, store visits, promotional events, or external covariates; do not attribute profit differences to these drivers.

## What would change a decision?
A review shortlist must show the size of the gap, comparison group, persistence over time, and missing evidence. Do not recommend interventions based on this synthetic model alone.
