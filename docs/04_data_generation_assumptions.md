# Product generation assumptions | v1

## Purpose

Create a reproducible product master that can support transaction-level retail simulations. This is a **synthetic model**, not a calibrated estimate of New Zealand retail pricing or margins.

## Design decisions

- **Grain:** one row per fictional product (`product_id`).
- **Scope:** `product_count` and `product_categories` are read from `config/generation.json`.
- **Category allocation:** products are assigned round-robin across configured categories. This creates approximately equal *SKU counts*, not equal sales mix or revenue.
- **Prices:** positive, right-skewed simulated base prices (lognormal, median approximately NZ$19, clipped to NZ$3–180, rounded to cents). These are ex-GST reference prices.
- **Costs:** category-specific target margin distributions are applied to reference prices; costs are rounded to cents. Margins are recomputed from rounded values.
- **Randomness:** a NumPy generator seeded by `random_seed` gives repeatable output with the same code and compatible library versions.
- **Product names:** generic placeholders, deliberately not brand or SKU claims.

## Category target gross margins (simulation parameters)

| Category | Target mean margin |
|---|---:|
| Health | 32% |
| Beauty | 40% |
| Skincare | 43% |
| Personal Care | 34% |
| Vitamins | 36% |
| Household | 24% |

Individual product target margins are drawn with 6.5 percentage-point standard deviation and clipped to 8–65%. These numbers are modelling choices, **not observed market benchmarks**.

## Known limitations

- `base_price_nzd` is not a transaction selling price; discounts and returns will be modelled later.
- `unit_cost_nzd` is a reference cost, not a purchase-order or time-varying inventory valuation.
- The model does not yet simulate category demand, store assortment, seasonality, promotions or supplier changes.
- Product category margin differences are intentionally encoded. Recovering those differences later is a validation exercise, not an independent real-world discovery.

## Quality gates

Unique product IDs; configured row count; valid categories; positive prices; non-negative costs not exceeding reference prices; correct derived margin; deterministic generation. Tests are in `tests/test_product_generation.py`.
