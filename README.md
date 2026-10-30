# Retail Profitability Intelligence

A reproducible, fictional New Zealand retail analytics portfolio project.

**Important:** Every store, financial figure, and operating assumption is synthetic. This is not Chemist Warehouse data. The simulated correlations are designed for demonstration and cannot establish real-world causes.

## Setup (macOS)

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
python src/generate_data.py
python -m pytest -q
python src/build_database.py
```

## Data grain
- `stores.csv`: one row per fictional store (60 stores)
- `store_month_financials.csv`: one row per store per month (Jan 2025–Sep 2026, 1,260 rows)

## Definitions
- Gross Profit = Net Sales - COGS
- GP Margin % = Gross Profit / Net Sales × 100
- Store Contribution = Gross Profit - Labour - Occupancy - Other Store Costs

This is a starting model, not a full accounting P&L. Later phases will expand category/product mix and strengthen scenario validity.
