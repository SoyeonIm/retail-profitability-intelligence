# Analysis log

## 2026-10-30 | First successful run
The generator produced 60 fictional stores and 1,260 store-month observations. Four starter tests passed and the DuckDB regional KPI query ran successfully on macOS.

Regional GP margins observed in the terminal output: Canterbury 30.21%, Wellington 30.10%, Otago 31.37%, Bay of Plenty 31.61%, Auckland 29.96%, Waikato 29.81%. The observed spread is 1.80 percentage points (rounded).

### Interpretation withheld
The regional gap is descriptive only. The current generator draws store-level GP rates randomly and applies regional factors to revenue. It does not encode a region-specific product mix or pricing mechanism. I will not claim that region explains GP performance from these aggregates.

### Next checks
- Confirm each store-month is unique and each financial month falls on/after the store's opening date.
- Check that aggregate GP margin is revenue-weighted.
- Inspect the distribution of store-level margins before selecting underperformers.
- Redesign the generator to include transaction-level commercial drivers, then document which patterns were intentionally simulated.

## 2026-10-30 — Baseline data audit

The initial dataset contains 60 fictional stores and
1,260 store-month financial records covering January
2025 to September 2026.

The baseline audit returned:
- Duplicate store-month keys: 0
- Missing store references: 0
- Pre-opening financial records: 0
- Missing financial amounts: 0
- Invalid sales/COGS records: 0

All six automated tests passed.

The current dataset is suitable for validating the
initial store-month reporting workflow. However,
it does not contain transaction-level sales or
product-level cost information.

This limits our ability to explain gross margin
differences through product mix, discounting,
or unit cost movements.

Next decision:
Extend the data model to transaction level while
preserving the existing baseline for comparison.